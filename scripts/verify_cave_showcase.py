"""Read-only verification of the registered qualitative showcase."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cave_composer.bundle import verify_portal_export, file_sha256
from cave_composer.portals import surface_path_certificate


def verify(folder):
    folder = Path(folder).resolve()
    scene = folder / 'scene'
    verify_portal_export(scene)
    portal = json.loads((scene / 'metadata/portal_validation.json').read_text())
    assert file_sha256(folder / 'reference_visual.npz') == portal['source_files']['visual/mesh.npz']
    config = json.loads((scene / 'metadata/source_config.json').read_text())
    safety = config['robot']['radius'] + config['robot']['margin']
    report = json.loads((folder / 'validation.json').read_text())
    records = json.loads((folder / 'assets/manifest.json').read_text())['assets']
    nav = json.loads((scene / 'navigation/centerline.json').read_text())['routes']
    routes = {r['id']: np.asarray(r['points']) for r in nav}
    tree = cKDTree(np.concatenate(list(routes.values())))
    spacing = max(np.linalg.norm(np.diff(r, axis=0), axis=1).max() for r in routes.values())
    assets = []
    for item in records:
        data = np.load(folder / 'assets' / item['mesh'])
        mesh = trimesh.Trimesh(data['vertices'], data['faces'], process=False)
        assert mesh.is_watertight and np.isfinite(mesh.vertices).all()
        for part in mesh.split(only_watertight=False):
            center = part.bounds.mean(0)
            bound = tree.query(center)[0] - spacing/2 - np.linalg.norm(part.vertices-center, axis=1).max()
            assert bound > safety
        assets.append(mesh)
    asset_mesh = trimesh.util.concatenate(assets)
    exported = np.load(folder / 'assets/collision.npz')
    assert np.array_equal(asset_mesh.vertices, exported['vertices'])
    assert np.array_equal(asset_mesh.faces, exported['faces'])
    path = np.asarray(json.loads((scene / 'navigation/portal_path.json').read_text())['points'])
    checks = {}
    for kind in ['visual', 'collision']:
        data = np.load(scene / kind / 'mesh.npz')
        mesh = trimesh.Trimesh(data['vertices'], data['faces'], process=False)
        checks[kind] = surface_path_certificate(trimesh.util.concatenate([mesh, asset_mesh]), path, safety)
        assert checks[kind]['status'] == 'PASS'
        assert abs(checks[kind]['continuous_clearance_lower_bound'] -
                   report['combined_mesh_path'][kind]['continuous_clearance_lower_bound']) < 1e-8
    cameras = json.loads((folder / 'views/registered_views.json').read_text())['views']
    assert len(cameras) == 8
    for v in cameras:
        position, target = np.asarray(v['position']), np.asarray(v['target'])
        matrix = np.asarray(v['matrix_world'])
        assert np.allclose(position, routes[v['route']][v['route_index']], atol=1e-8)
        assert np.allclose(matrix[:3, 3], position, atol=1e-5)
        direction = (target-position) / np.linalg.norm(target-position)
        assert np.dot(-matrix[:3, 2], direction) > .99999
        assert all(0 < x < 100 for x in v['map_percent'])
        with Image.open(folder / v['image']) as image:
            assert image.size == (1800, 1125)
            image.verify()
    with Image.open(folder / 'figures/cave_showcase.png') as image:
        assert image.size == (6000, 3600)
        image.verify()
    for name in ['index.html', 'cave_showcase.blend', 'figures/cave_showcase.pdf', 'figures/caption.txt']:
        assert (folder / name).stat().st_size > 100
    return dict(status='PASS', assets=len(assets), registered_views=len(cameras),
                required_radius=safety, combined_mesh_path=checks,
                checks=['portal integrity', 'closed reference hash', 'watertight asset components',
                        'all-route bounding-ball exclusion', 'exported asset collision arrays',
                        'actual dual-mesh path distances', 'camera locations and orientations', 'image sizes'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', default='outputs/cave_showcase_v01')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = verify(args.folder)
    if args.report:
        args.report.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
