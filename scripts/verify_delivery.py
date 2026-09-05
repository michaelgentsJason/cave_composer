"""Audit delivered evidence and refresh metadata hashes after presentation/adapter edits."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cave_composer.pipeline import dump, mesh_digest, attach_intersection_audit


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='outputs')
    parser.add_argument('--refresh-hashes', action='store_true')
    args = parser.parse_args()
    root = Path(args.root)
    scenes = sorted((root/'final').glob('cave_*'))
    assert len(scenes) == 6, 'Expected six final cave bundles'
    result = {'scope':'offline v0 delivery; not simulator or learning validation','scenes':[], 'reproducibility':[], 'batches':[]}
    required = ['visual/cave_visual.obj','visual/cave_visual.mtl','visual/mesh.npz',
                'collision/cave_collision.obj','collision/mesh.npz','materials/rock_albedo.png',
                'materials/material.json','navigation/centerline.json','navigation/navigation_graph.json',
                'navigation/junction_graph.json','navigation/spawn_points.json','navigation/goals.json',
                'navigation/clearance.json','navigation/visibility_horizon.json','metadata/config.yaml',
                'metadata/metrics.json','metadata/provenance.json','metadata/validation.json',
                'metadata/intersection_audit.json','cave.blend','stonefish/cave.scn','stonefish/adapter.json']
    for folder in scenes:
        for name in required:
            assert (folder/name).is_file() and (folder/name).stat().st_size > 0, folder/name
        report = json.loads((folder/'metadata/validation.json').read_text())
        audit = json.loads((folder/'metadata/intersection_audit.json').read_text())
        if args.refresh_hashes:
            attach_intersection_audit(report, audit)
            dump(folder/'metadata/validation.json', report)
        assert report['status']=='VALID' and all(report['checks'].values()), folder
        assert audit['status']=='PASS', folder
        assert report['revalidation']['collision_regenerated_identically'], folder
        assert report['revalidation']['validator_source_sha256'] == sha(Path(__file__).resolve().parents[1]/'cave_composer/validation.py')
        provenance = json.loads((folder/'metadata/provenance.json').read_text())
        for kind in ['visual','collision']:
            with np.load(folder/kind/'mesh.npz') as data:
                mesh = trimesh.Trimesh(data['vertices'],data['faces'],process=False)
            assert mesh_digest(mesh)==provenance[kind+'_mesh_sha256'], folder
            assert report['mesh'][kind]['continuous_polyline_clearance_lower_bound']>report['robot_safety_radius']
        dimensions = {}
        for view in ['overview','inside_01','inside_02','topology']:
            with Image.open(folder/'previews'/f'{view}.png') as im:
                dimensions[view]=list(im.size); im.verify()
        xml = ET.parse(folder/'stonefish/cave.scn').getroot()
        assert xml.find('static/physical/mesh').attrib['convex']=='false'
        for mesh in xml.findall('.//mesh'):
            assert (folder/mesh.attrib['filename']).is_file()
        for look in xml.findall('looks/look'):
            if look.get('texture'): assert (folder/look.get('texture')).is_file()
        manifest = {p.relative_to(folder).as_posix():sha(p) for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='checksums.json'}
        if args.refresh_hashes: dump(folder/'metadata/checksums.json',manifest)
        assert json.loads((folder/'metadata/checksums.json').read_text())==manifest, f'Stale checksums: {folder}'
        result['scenes'].append({'scene':folder.name,'status':'PASS','files_hashed':len(manifest),
            'mesh_identity_verified':True,'collision_reproduced':True,'previews':dimensions,
            'collision_clearance_lower_bound':report['mesh']['collision']['continuous_polyline_clearance_lower_bound'],
            'bvh_status':audit['status'],'stonefish_xml_references':'PASS; runtime not tested'})
    for name in ['batch_final_parallel','batch_final_serial','ood_geometry_smoke','ood_composition_smoke']:
        manifest = json.loads((root/name/'manifest.json').read_text())
        assert manifest['valid']==manifest['requested'] and manifest['invalid']==0
        result['batches'].append({'name':name,'requested':manifest['requested'],'valid':manifest['valid'],'workers':manifest['workers']})
    for a in sorted((root/'batch_final_parallel').glob('scene_*')):
        b = root/'batch_final_serial'/a.name
        pa = json.loads((a/'metadata/provenance.json').read_text())
        pb = json.loads((b/'metadata/provenance.json').read_text())
        keys = ['seed','geometry_config_sha256','visual_mesh_sha256','collision_mesh_sha256']
        checks = {key:pa[key]==pb[key] for key in keys}
        for rel in ['visual/cave_visual.obj','collision/cave_collision.obj','visual/mesh.npz','collision/mesh.npz']:
            checks[rel] = sha(a/rel)==sha(b/rel)
        assert all(checks.values()), a
        result['reproducibility'].append({'scene':a.name,'checks':checks})
    assert len(result['reproducibility'])==4
    experiment = root/'material_experiment/cavers_transfer'
    material = json.loads((experiment/'experiment.json').read_text())
    styled = experiment/'cave_b_cavers'
    baseline = root/'final/cave_b_sharp_turns'
    checks = {rel:sha(baseline/rel)==sha(styled/rel) for rel in ['visual/cave_visual.obj','collision/cave_collision.obj','visual/mesh.npz','collision/mesh.npz']}
    assert all(checks.values()) and material['original_files_unchanged']
    source_checks = {prior['prior_source']:sha(Path(prior['prior_source']))==prior['source_sha256'] for prior in material['priors']}
    assert all(source_checks.values())
    result['cavers']={'geometry_byte_identity':checks,'source_files_unchanged':source_checks,'pbr_recovery':'PARTIAL; palette only, roughness assumed'}
    result['status']='PASS'
    dump(root/'final/acceptance_evidence.json',result)
    print(json.dumps({'status':result['status'],'final_scenes':len(scenes),'parallel_serial_matches':len(result['reproducibility']),'batches':result['batches'],'cavers':'PASS'},indent=2))


if __name__=='__main__':
    main()
