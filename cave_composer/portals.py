"""Optional terminal-portal export from a validated CLOSED reference bundle.

An open surface has no reliable parity-inside test. Keep the closed reference
and its certificates separate, check exactly two intentional boundary loops,
and check the swept sphere against the actual open surfaces. Terminal planes
are deliberately conservative: layouts cut elsewhere by those planes fail.
"""
from pathlib import Path
import json
import shutil
import uuid

import numpy as np
import trimesh

from .bundle import atomic_json, bundle_checksums, file_sha256, verify_bundle
from .export import write_obj
from .planning import certify_polyline
from .validation import mesh_clearance


def terminal_planes(points):
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < 2 or not np.isfinite(points).all():
        raise ValueError('Expected a finite main route')
    normals = np.array([points[1] - points[0], points[-2] - points[-1]])
    lengths = np.linalg.norm(normals, axis=1)
    if np.any(lengths < 1e-8):
        raise ValueError('Terminal directions must be nonzero')
    return points[[0, -1]], normals / lengths[:, None]


def boundary_loops(mesh, origins, normals, tolerance=1e-5):
    edges, counts = np.unique(mesh.edges_sorted, axis=0, return_counts=True)
    if np.any(counts > 2):
        raise ValueError('Nonmanifold edge in portal surface')
    boundary = edges[counts == 1]
    adjacency = {}
    for a, b in boundary:
        adjacency.setdefault(int(a), []).append(int(b))
        adjacency.setdefault(int(b), []).append(int(a))
    if not adjacency or any(len(v) != 2 for v in adjacency.values()):
        raise ValueError('Portal boundary must consist of closed, nonbranching loops')
    pending, loops = set(adjacency), []
    while pending:
        first = min(pending)
        loop, previous, current = [], None, first
        while True:
            loop.append(current)
            pending.discard(current)
            choices = adjacency[current]
            nxt = choices[0] if choices[0] != previous else choices[1]
            previous, current = current, nxt
            if current == first:
                break
            if current not in pending:
                raise ValueError('Invalid boundary cycle')
        loops.append(np.array(loop, dtype=int))
    if len(loops) != 2:
        raise ValueError(f'Expected exactly entrance and exit loops; found {len(loops)}')
    records = {}
    for loop in loops:
        vertices = mesh.vertices[loop]
        errors = [float(np.abs((vertices - p) @ n).max()) for p, n in zip(origins, normals)]
        which = int(np.argmin(errors))
        if errors[which] > tolerance or which in records:
            raise ValueError('Additional hole or ambiguous terminal opening')
        records[which] = {'name': ['entrance', 'exit'][which],
                          'vertices': vertices.tolist(), 'edge_count': len(loop),
                          'plane_max_error_metres': errors[which]}
    return [records[i] for i in range(2)]


def open_terminal_mesh(mesh, origins, normals, routes):
    if not mesh.is_watertight or not mesh.is_winding_consistent:
        raise ValueError('Portal export requires a closed, consistently wound reference mesh')
    points = np.concatenate(routes)
    for p, n in zip(origins, normals):
        if np.any((points - p) @ n < -1e-6):
            raise ValueError('Terminal clipping plane crosses another intended route; choose a compatible layout')
    result = mesh.copy()
    for p, n in zip(origins, normals):
        # Use triangle clipping directly; no polygon filling or Shapely required.
        vertices, faces, _ = trimesh.intersections.slice_faces_plane(
            result.vertices, result.faces, plane_normal=n, plane_origin=p)
        result = trimesh.Trimesh(vertices, faces, process=False)
    result.merge_vertices(digits_vertex=8)
    # A plane through existing lattice vertices can produce zero-area slivers.
    # Remove only those faces, then require closed boundary loops below.
    nonzero = result.area_faces > 1e-12
    result.metadata['removed_zero_area_faces'] = int((~nonzero).sum())
    result.update_faces(nonzero)
    result.remove_unreferenced_vertices()
    if not len(result.faces) or not np.isfinite(result.vertices).all() or not result.is_winding_consistent:
        raise ValueError('Invalid clipped surface')
    if result.area_faces.min() <= 1e-12:
        raise ValueError('Degenerate portal triangle')
    components = result.split(only_watertight=False)
    # Separate closed rock formations can already exist inside the source void.
    # Retain them, while requiring exactly one wall component with openings.
    if (len(components) != len(mesh.split(only_watertight=False))
            or sum(not c.is_watertight for c in components) != 1):
        raise ValueError('Terminal clipping changed wall/rock component structure')
    result.metadata['closed_rock_components'] = sum(c.is_watertight for c in components)
    loops = boundary_loops(result, origins, normals)
    return result, loops


def surface_path_certificate(mesh, points, safety, sample_step=.20):
    """Unsigned distance suffices for collision with an OPEN triangle surface.

    This does not determine cavity membership. The exporter separately verifies
    the interior portion in the closed source and extends only across portals.
    """
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < 2 or not np.isfinite(points).all():
        raise ValueError('Expected a finite polyline with at least two points')
    if not np.isfinite(safety) or safety <= 0 or not np.isfinite(sample_step) or sample_step <= 0:
        raise ValueError('Safety and sampling step must be positive and finite')
    samples = [points[0]]
    maximum_step = 0.
    for a, b in zip(points[:-1], points[1:]):
        length = float(np.linalg.norm(b - a))
        count = max(1, int(np.ceil(length / sample_step)))
        maximum_step = max(maximum_step, length / count)
        samples.extend(np.linspace(a, b, count + 1)[1:])
    distances = mesh_clearance(mesh, np.asarray(samples))
    lower = float(distances.min() - maximum_step / 2)
    return {'status': 'PASS' if lower > safety else 'FAIL', 'samples': len(samples),
            'sample_max_step': maximum_step, 'minimum_sampled_clearance': float(distances.min()),
            'continuous_clearance_lower_bound': lower, 'required_radius': float(safety),
            'method': 'distance to open triangles minus half maximum sample spacing; no open-mesh contains test'}


def export_portals(source, output, outside_distance=3.):
    source, output = Path(source).resolve(), Path(output).resolve()
    if not np.isfinite(outside_distance) or outside_distance <= 0:
        raise ValueError('Outside approach distance must be positive and finite')
    if output == source or source in output.parents or output in source.parents:
        raise ValueError('Portal output must be separate from the reference bundle')
    if output.exists():
        raise FileExistsError(output)
    verify_bundle(source)
    config = json.loads((source / 'metadata/config.json').read_text(encoding='utf-8'))
    nav = json.loads((source / 'navigation/centerline.json').read_text(encoding='utf-8'))
    planned = json.loads((source / 'navigation/planned_path.json').read_text(encoding='utf-8'))
    if planned.get('status') != 'PASS':
        raise ValueError('Source must contain a successful independent path')
    routes = [np.asarray(r['points']) for r in nav['routes']]
    origins, normals = terminal_planes(routes[0])
    interior = np.vstack([origins[0], planned['points'], origins[1]])
    exterior = origins - outside_distance * normals
    through = np.vstack([exterior[0], interior, exterior[1]])
    safety = config['robot']['radius'] + config['robot']['margin']
    report = {'status': 'FAIL', 'artifact_type': 'open_portal_export',
              'source_bundle': str(source), 'source_checksums_sha256': file_sha256(source / 'metadata/checksums.json'),
              'source_files': {p: file_sha256(source / p) for p in [
                  'visual/mesh.npz', 'collision/mesh.npz', 'navigation/planned_path.json', 'metadata/config.json']},
              'method': 'uncapped terminal halfspace clipping of both final reference meshes',
              'meshes': {}, 'portals': [
                  {'name': name, 'center': p.tolist(), 'inward': n.tolist(), 'outside_point': e.tolist()}
                  for name, p, n, e in zip(['entrance', 'exit'], origins, normals, exterior)],
              'limitations': ['Open surface export; intentionally not watertight and not a solid rock volume.',
                             'Only compatible terminal layouts are supported; no surrounding terrain or exterior navigation domain.',
                             'Interior path reuses the independently searched source path; exterior approaches are straight constructed segments.',
                             'Geometric spherical-envelope checks, not robot dynamics or controller evaluation.']}
    meshes = {}
    for kind in ['visual', 'collision']:
        with np.load(source / kind / 'mesh.npz') as data:
            reference = trimesh.Trimesh(data['vertices'], data['faces'], process=False)
        reference_certificate = certify_polyline(reference, interior, safety)
        if reference_certificate['status'] != 'PASS':
            raise ValueError(f'{kind}: interior approach fails closed-reference certificate')
        mesh, loops = open_terminal_mesh(reference, origins, normals, routes)
        crossing = surface_path_certificate(mesh, through, safety)
        if crossing['status'] != 'PASS':
            raise ValueError(f'{kind}: crossing path too close to open surface')
        meshes[kind] = mesh
        report['meshes'][kind] = {
            'watertight': bool(mesh.is_watertight), 'winding_consistent': bool(mesh.is_winding_consistent),
            'triangles': len(mesh.faces), 'boundary_loops': loops,
            'removed_zero_area_faces': mesh.metadata.get('removed_zero_area_faces', 0),
            'retained_closed_rock_components': mesh.metadata.get('closed_rock_components', 0),
            'closed_reference_interior_certificate': reference_certificate, 'crossing_certificate': crossing}
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_name('.' + output.name + '.building-' + uuid.uuid4().hex[:8])
    temp.mkdir()
    for folder in ['visual', 'collision', 'navigation', 'metadata', 'materials', 'previews']:
        (temp / folder).mkdir()
    for p in (source / 'materials').iterdir():
        if p.is_file():
            shutil.copy2(p, temp / 'materials' / p.name)
    for name in ['config.json', 'validation.json']:
        shutil.copy2(source / 'metadata' / name, temp / 'metadata' / ('source_' + name))
    shutil.copy2(source / 'navigation/centerline.json', temp / 'navigation/centerline.json')
    for kind, mesh in meshes.items():
        np.savez_compressed(temp / kind / 'mesh.npz', vertices=mesh.vertices, faces=mesh.faces)
        write_obj(mesh, temp / kind / f'cave_{kind}.obj', visual=kind == 'visual')
    report['status'] = 'PASS'
    atomic_json(temp / 'metadata/portal_validation.json', report)
    atomic_json(temp / 'navigation/portal_path.json', {
        'points': through.tolist(), 'start': exterior[0].tolist(), 'goal': exterior[1].tolist(),
        'interior_path_source': 'source independent A* plus verified terminal connectors',
        'exterior_path_source': 'straight approaches crossing the two terminal planes'})
    (temp / 'README.txt').write_text(
        'OPEN PORTAL DERIVATIVE\nTwo intentional openings in both meshes.\n'
        'See metadata/portal_validation.json for boundary and crossing checks.\n'
        'The original closed-bundle validation applies only to the reference.\n'
        'This folder is not a historical v0.3 sealed scene bundle.\n', encoding='utf-8')
    atomic_json(temp / 'metadata/checksums.json', bundle_checksums(temp))
    temp.rename(output)
    return report
