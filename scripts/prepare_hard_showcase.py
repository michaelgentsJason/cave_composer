"""Prepare a registered 12-view derivative of the delivered hard_005 cave."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cave_composer.bundle import file_sha256, verify_portal_export
from scripts.prepare_cave_showcase import prepare, save_json


def main(folder, asset):
    folder, asset = Path(folder).resolve(), Path(asset).resolve()
    meta = json.loads((asset/'metadata.json').read_text())
    source = Path(meta['open'])
    folder.mkdir(parents=True, exist_ok=True)
    if not (folder/'scene').exists():
        if source.exists():
            verify_portal_export(source)
            shutil.copytree(source, folder/'scene')
        else:
            # A fresh clone contains the portable config and closed visual
            # reference. Replay once and reject any geometric drift.
            from cave_composer.pipeline import generate
            from cave_composer.portals import export_portals
            reference=folder/'reference'
            generate(str(asset/'config.json'),meta['seed'],str(reference),render=False)
            with np.load(reference/'visual/mesh.npz') as replay, np.load(asset/'reference_visual.npz') as original:
                if not all(np.array_equal(replay[k],original[k]) for k in ['vertices','faces']):
                    raise ValueError('Replayed geometry differs from delivered hard_005 reference')
            export_portals(reference,folder/'scene',terminal_inset=meta.get('terminal_inset_metres',0))
    source=folder/'scene'
    verify_portal_export(folder/'scene')
    routes = json.loads((source/'navigation/centerline.json').read_text())['routes']
    # Main passage, both bypass loops, and both blind branches; all targets
    # follow the same route. These are inspection poses, not executed episodes.
    requests = [(0,.08,'Entrance passage'), (0,.31,'Main junction'),
                (0,.56,'Chamber approach'), (0,.97,'Open exit'),
                (1,.20,'First bypass'), (1,.52,'First loop bend'),
                (1,.83,'First loop return'), (2,.22,'Second bypass'),
                (2,.54,'Second loop bend'), (2,.84,'Second loop return'),
                (3,.64,'Long blind branch'), (4,.62,'Short blind branch')]
    specifications=[]
    for route_id, fraction, title in requests:
        n=len(routes[route_id]['points'])
        index=round((n-1)*fraction)
        specifications.append((route_id,index,min(index+22,n-1),title))
    save_json(folder/'source.json', dict(asset=asset.relative_to(Path.cwd()).as_posix(),
        seed=meta['seed'], source_name=meta['name'], total_route_length_m=meta['total_route_length_m'],
        main_route_length_m=meta['main_route_length_m'], loops=meta['loops'], dead_ends=meta['dead_ends'],
        source_mesh_sha256=file_sha256(source/'visual/mesh.npz'),
        asset_sha256={p.name:file_sha256(p) for p in [asset/'config.json',asset/'reference_visual.npz',asset/(meta['name']+'.glb')]},
        map_rotation_degrees=-23, geometry_regenerated=False))
    prepare(folder,specifications,resolution=(1600,1200))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder',default='outputs/cave_showcase_hard_v02')
    parser.add_argument('--asset',default='exports/caves_difficulty_v01/hard/scene_005')
    args=parser.parse_args()
    main(args.folder,args.asset)
