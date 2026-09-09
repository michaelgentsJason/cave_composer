"""Check standalone GLB/OBJ texture references, geometry and portal paths."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import sys

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cave_composer.portals import boundary_loops, surface_path_certificate


def load_world_mesh(path):
    scene = trimesh.load(path, force='scene', process=False)
    items = []
    for node in scene.graph.nodes_geometry:
        transform, geometry = scene.graph[node]
        item = scene.geometry[geometry].copy()
        item.apply_transform(transform)
        items.append(item)
    result = trimesh.util.concatenate(items)
    if path.suffix == '.glb':
        # Convert glTF world Y-up back to the source/OBJ Z-up frame.
        result.vertices = np.asarray(result.vertices)[:, [0, 2, 1]] * [1, -1, 1]
        # Direct vertex reassignment above is a proper rotation (determinant +1).
    # UV/normal seams split render vertices without opening the physical wall.
    result.merge_vertices(merge_tex=True, merge_norm=True, digits_vertex=12)
    return result


def portable_reference(folder):
    """Use only files carried with the exports, never workstation provenance paths."""
    folder = Path(folder)
    config = json.loads((folder/'config.json').read_text(encoding='utf-8'))
    report = json.loads((folder/'export_verification.json').read_text(encoding='utf-8'))
    with np.load(folder/'reference_visual.npz') as data:
        vertices, triangles = data['vertices'].copy(), len(data['faces'])
    return vertices, triangles, config['robot']['radius'] + config['robot']['margin'], report['texture_resolution']


def verify(root, report_path=None, entries=None):
    if not __debug__:
        raise RuntimeError('Run verification without -O; assertion checks must remain enabled')
    root = Path(root).resolve()
    records = []
    if entries is None:
        manifest = root / 'batch_manifest.json'
        entries = json.loads(manifest.read_text(encoding='utf-8'))['assets'] if manifest.exists() else [
            {'difficulty': tier, 'folder': tier, 'name': f'cave_{tier}'}
            for tier in ['easy', 'medium', 'hard']]
    for entry in entries:
        tier, name = entry['difficulty'], entry['name']
        folder = (root / entry['folder']).resolve()
        if root not in folder.parents or Path(name).name != name or any(c in name for c in '/\\:'):
            raise ValueError('Asset paths must stay inside the export root')
        reference, triangles, safety, resolution = portable_reference(folder)
        raw = (folder / f'{name}.glb').read_bytes()
        magic, version, total = struct.unpack_from('<4sII', raw)
        assert magic == b'glTF' and version == 2 and total == len(raw)
        size, kind = struct.unpack_from('<II', raw, 12)
        assert kind == 0x4E4F534A
        gltf = json.loads(raw[20:20 + size])
        binary_size, binary_kind = struct.unpack_from('<II', raw, 20 + size)
        assert binary_kind == 0x004E4942
        binary = raw[28 + size:28 + size + binary_size]
        assert len(binary) == binary_size and all('uri' not in b for b in gltf['buffers'])
        embedded = []
        for image in gltf['images']:
            assert 'uri' not in image and 'bufferView' in image
            view = gltf['bufferViews'][image['bufferView']]
            offset = view.get('byteOffset', 0)
            payload = binary[offset:offset + view['byteLength']]
            im = Image.open(io.BytesIO(payload))
            im.load()
            assert im.size == (resolution, resolution)
            embedded.append({'mime': image['mimeType'], 'size': list(im.size),
                             'sha256': hashlib.sha256(payload).hexdigest()})
        assert len(embedded) >= 2
        for material in gltf['materials']:
            assert 'baseColorTexture' in material['pbrMetallicRoughness']
            assert 'normalTexture' in material and material.get('doubleSided') is True
        obj_path = folder / f'{name}.obj'
        text = obj_path.read_text()
        assert 'vt ' in text and 'usemtl ' in text
        mtl_name = next(l.split(maxsplit=1)[1] for l in text.splitlines() if l.startswith('mtllib '))
        mtl = (folder / mtl_name).read_text()
        texture_refs = []
        for line in mtl.splitlines():
            if line.startswith('map_'):
                ref = line.split()[-1]
                assert not Path(ref).is_absolute() and (folder / ref).is_file()
                texture_refs.append(ref)
        assert 'textures/basecolor.png' in texture_refs and 'textures/normal.png' in texture_refs
        portal = json.loads((folder / 'portal_validation.json').read_text())
        origins = np.array([p['center'] for p in portal['portals']])
        normals = np.array([p['inward'] for p in portal['portals']])
        points = json.loads((folder / 'navigation_z_up.json').read_text())['points']
        row = {'difficulty': tier, 'name': name, 'folder': entry['folder'], 'status': 'PASS', 'embedded_glb_images': embedded,
               'obj_relative_texture_paths': texture_refs, 'formats': {}}
        for ext in ['glb', 'obj']:
            mesh = load_world_mesh(folder / f'{name}.{ext}')
            cleanup = json.loads((folder / 'precision_cleanup.json').read_text())[ext]
            assert cleanup['triangles_before'] == triangles
            assert len(mesh.faces) == cleanup['triangles_after']
            assert mesh.area_faces.min() > 1e-12
            delta = max(cKDTree(reference).query(mesh.vertices)[0].max(),
                        cKDTree(mesh.vertices).query(reference)[0].max())
            assert delta < 1e-4, (tier, ext, delta)
            loops = boundary_loops(mesh, origins, normals, tolerance=2e-5)
            certificate = surface_path_certificate(mesh, points, safety)
            assert certificate['status'] == 'PASS'
            row['formats'][ext] = {'triangles': len(mesh.faces), 'openings': len(loops),
                                  'geometry_max_position_difference_m': float(delta),
                                  'crossing_certificate': certificate}
        records.append(row)
        print(name, 'textures, geometry, two portals, crossing path PASS', flush=True)
    if report_path is not None:
        Path(report_path).write_text(json.dumps(records, indent=2), encoding='utf-8')
    return records


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='exports/caves_difficulty_v01')
    parser.add_argument('--report', help='Optional result file; default verification is read-only')
    args = parser.parse_args()
    verify(args.root, args.report)
