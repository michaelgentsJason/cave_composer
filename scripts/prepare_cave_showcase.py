"""Prepare a reproducible qualitative showcase from an existing open cave.

No cave regeneration. Asset collision geometry is the geometry sent to Blender.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.spatial import cKDTree
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cave_composer.bundle import verify_portal_export, file_sha256
from cave_composer.portals import surface_path_certificate


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2), encoding='utf-8')


def prepare(folder):
    folder = Path(folder).resolve()
    scene = folder / 'scene'
    verify_portal_export(scene)
    for name in ['assets', 'views', 'figures']:
        (folder / name).mkdir(exist_ok=True)
    nav = json.loads((scene / 'navigation/centerline.json').read_text())
    routes = [np.asarray(r['points']) for r in nav['routes']]
    config = json.loads((scene / 'metadata/source_config.json').read_text())
    portal_report = json.loads((scene / 'metadata/portal_validation.json').read_text())
    reference_file = folder / 'reference_visual.npz'
    if not reference_file.exists():
        shutil.copy2(Path(portal_report['source_bundle']) / 'visual/mesh.npz', reference_file)
    if file_sha256(reference_file) != portal_report['source_files']['visual/mesh.npz']:
        raise ValueError('Closed reference mesh checksum differs from portal provenance')
    reference_data = np.load(reference_file)
    closed = trimesh.Trimesh(reference_data['vertices'], reference_data['faces'], process=False)
    safety = config['robot']['radius'] + config['robot']['margin']
    meshes = {}
    for kind in ['visual', 'collision']:
        data = np.load(scene / kind / 'mesh.npz')
        meshes[kind] = trimesh.Trimesh(data['vertices'], data['faces'], process=False)
    visual = meshes['visual']
    rng = np.random.default_rng(20260908)
    all_route = np.concatenate(routes)
    tree = cKDTree(all_route)
    route_spacing = max(np.linalg.norm(np.diff(r, axis=0), axis=1).max() for r in routes)
    assets, asset_meshes = [], []

    def floor_at(p):
        hits, _, _ = visual.ray.intersects_location([p], [[0, 0, -1]], multiple_hits=True)
        if len(hits) == 0:
            return None
        return hits[np.argmin(np.linalg.norm(hits - p, axis=1))]

    def accept(mesh, name, kind, material_name, extra=None):
        # A bounding ball encloses the entire asset, including the stand.
        # Distance to route samples minus h/2 extends to every route segment.
        center = mesh.bounds.mean(0)
        parts = mesh.split(only_watertight=False) if kind == 'checkerboard' else [mesh]
        lower = min(float(tree.query(part.bounds.mean(0))[0] - route_spacing / 2
                    - np.linalg.norm(part.vertices - part.bounds.mean(0), axis=1).max())
                    for part in parts)
        if lower <= safety + .025:
            return False
        filename = name + '.npz'
        np.savez_compressed(folder / 'assets' / filename, vertices=mesh.vertices, faces=mesh.faces)
        item = dict(name=name, kind=kind, material=material_name, mesh=filename,
                    center=center.tolist(), bounds=mesh.bounds.tolist(),
                    all_construction_routes_bounding_ball_clearance=lower)
        item.update(extra or {})
        assets.append(item)
        asset_meshes.append(mesh)
        return True

    # Scatter only on the floor, outside a conservatively protected route tube.
    for route_id, r in enumerate(routes):
        for index in range(12, len(r) - 12, 13):
            p = r[index]
            t = r[index + 2] - r[index - 2]
            t /= np.linalg.norm(t)
            side = np.array([-t[1], t[0], 0.])
            side /= np.linalg.norm(side)
            for sign in [-1, 1]:
                q = p + side * sign * rng.uniform(.85, 1.6)
                if tree.query(q)[0] < .7:
                    continue
                hit = floor_at(q)
                if hit is None or not .8 < q[2] - hit[2] < 4:
                    continue
                rock = trimesh.creation.icosphere(subdivisions=2)
                scale = rng.uniform([.16, .13, .12], [.47, .36, .32])
                rock.vertices *= rng.uniform(.82, 1.16, (len(rock.vertices), 1)) * scale
                rock.apply_transform(trimesh.transformations.rotation_matrix(rng.uniform(0, 6.28), [0, 0, 1]))
                # Seat the lowest vertex slightly into the receiving floor.
                rock.apply_translation(hit + [0, 0, -rock.vertices[:, 2].min() - .035])
                accept(rock, f'rock_{len(assets):03d}', 'rock', 'rock')

    # Camera locations belong to the original construction routes; they are not
    # a claimed executed robot trajectory. Look targets follow local bends.
    specifications = [
        (0, 18, 45, 'Entrance junction'),
        (1, 24, 49, 'First loop approach'),
        (1, 107, 131, 'First loop return'),
        (0, 145, 175, 'Second junction'),
        (2, 42, 66, 'Second loop bend'),
        (2, 121, 148, 'Loop return passage'),
        (0, 340, 365, 'Descending bend'),
        (0, len(routes[0]) - 15, len(routes[0]) - 1, 'Open exit'),
    ]
    views = []
    for number, (route_id, index, target_index, title) in enumerate(specifications, 1):
        r = routes[route_id]
        position, target = r[index].copy(), r[target_index].copy()
        views.append(dict(id=number, title=title, route=nav['routes'][route_id]['id'],
                          route_index=index, position=position.tolist(), target=target.tolist(),
                          lens_mm=19, sensor_width_mm=36, image=f'views/view_{number:02d}.png'))

    # Three freestanding checkerboard props, positioned beside the passage.
    # Each board is an exact 8 x 6 pattern with 80 mm squares (visual prop).
    for board_id, view_id in enumerate([1, 3, 6], 1):
        view = views[view_id - 1]
        route_id = [r['id'] for r in nav['routes']].index(view['route'])
        r = routes[route_id]
        idx = min(view['route_index'] + 15, len(r) - 4)
        tangent = r[idx + 2] - r[idx - 2]
        tangent[2] = 0
        tangent /= np.linalg.norm(tangent)
        side = np.array([-tangent[1], tangent[0], 0.])
        placed = False
        for advance, offset in [(a, o) for a in [15, 12, 18, 9, 21, 24, 27]
                                for o in [1.3, -1.3, 1.5, -1.5, 1.7, -1.7, 1.9, -1.9]]:
            idx = min(view['route_index'] + advance, len(r) - 4)
            tangent = r[idx + 2] - r[idx - 2]
            tangent[2] = 0
            tangent /= np.linalg.norm(tangent)
            side = np.array([-tangent[1], tangent[0], 0.])
            center = r[idx] + side * offset + [0, 0, -.2]
            floor = floor_at(center)
            if floor is None or not .5 < center[2] - floor[2] < 3.5:
                continue
            # Columns: horizontal board axis, thickness axis, vertical.
            rotation = np.column_stack([side, -tangent, [0, 0, 1.]])
            if np.linalg.det(rotation) < 0:
                rotation[:, 0] *= -1
            frame = trimesh.creation.box([.78, .05, .74])
            frame.vertices = frame.vertices @ rotation.T + center
            stand_height = center[2] - .37 - floor[2]
            if stand_height <= .08:
                continue
            stand = trimesh.creation.cylinder(radius=.022, height=stand_height, sections=12)
            stand.apply_translation([center[0], center[1], floor[2] + stand_height / 2])
            base = trimesh.creation.box([.28, .24, .045])
            base.apply_translation([center[0], center[1], floor[2] + .012])
            group = trimesh.util.concatenate([frame, stand, base])
            # Validate board corners remain in the cavity using closed reference.
            if not closed.contains(frame.vertices).all():
                continue
            if accept(group, f'board_{board_id:02d}', 'checkerboard', 'metal', dict(
                    board_center=center.tolist(), rotation=rotation.tolist(),
                    squares=[8, 6], square_size_m=.08, associated_view=view_id)):
                placed = True
                break
        if not placed:
            raise ValueError(f'No safe board placement for view {view_id}')

    # Recheck the actual full portal-to-portal path against the added triangles.
    through = np.asarray(json.loads((scene / 'navigation/portal_path.json').read_text())['points'])
    combined_assets = trimesh.util.concatenate(asset_meshes)
    asset_cert = surface_path_certificate(combined_assets, through, safety)
    if asset_cert['status'] != 'PASS':
        raise ValueError('Added assets obstruct the original path')
    certificates = {}
    for kind, mesh in meshes.items():
        combined = trimesh.util.concatenate([mesh, combined_assets])
        certificates[kind] = surface_path_certificate(combined, through, safety)
        if certificates[kind]['status'] != 'PASS':
            raise ValueError(f'Combined {kind} path failed')
    camera_cert = []
    for view in views:
        p = np.asarray(view['position'])
        _, d, _ = trimesh.proximity.closest_point(trimesh.util.concatenate([visual, combined_assets]), [p])
        camera_cert.append(float(d[0]))
    if min(camera_cert) <= safety:
        raise ValueError('Camera is too close to geometry')
    np.savez_compressed(folder / 'assets/collision.npz', vertices=combined_assets.vertices, faces=combined_assets.faces)
    save_json(folder / 'assets/manifest.json', dict(seed=20260908, coordinate_system='meters, Z up',
        assets=assets, navigation_protection='Bounding balls exclude all construction-route segments; actual combined meshes checked on portal path.'))
    save_json(folder / 'views/cameras.json', dict(views=views, resolution=[1800, 1125],
        convention='world meters Z up; Blender camera looks along local -Z with local Y up'))
    save_json(folder / 'validation.json', dict(status='PASS', required_radius=safety,
        original_source=config['name'], asset_count=len(assets),
        rock_count=sum(a['kind'] == 'rock' for a in assets), board_count=3,
        assets_only_path=asset_cert, combined_mesh_path=certificates,
        minimum_asset_to_construction_route_bound=min(a['all_construction_routes_bounding_ball_clearance'] for a in assets),
        camera_surface_distances=camera_cert,
        scope='Existing independent interior A* with verified terminal connectors and straight exterior approaches. No dynamics or sensor simulation.'))
    # Self-created image, no third-party texture/license dependency.
    image = Image.new('RGB', (888, 840), '#d5d2c8')
    draw = ImageDraw.Draw(image)
    for y in range(6):
        for x in range(8):
            draw.rectangle([60 + x * 96, 70 + y * 96, 59 + (x+1)*96, 69 + (y+1)*96],
                           fill='#101214' if (x+y) % 2 == 0 else '#eeeee8')
    try:
        font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 37)
    except OSError:
        font = ImageFont.load_default()
    draw.text((60, 703), 'CAVE COMPOSER', font=font, fill='#292e31')
    draw.text((60, 758), '8 x 6  |  80 mm squares', font=font, fill='#292e31')
    image.save(folder / 'assets/checkerboard.png')
    print(json.dumps(dict(assets=len(assets), certificates=certificates), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', default='outputs/cave_showcase_v01')
    prepare(parser.parse_args().folder)
