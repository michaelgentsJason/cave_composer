"""Verified multi-task packs on immutable generated caves.

Semantic routes select endpoint requests only. Each solution is independently
searched in occupancy and certified on both final meshes. Every request,
including a rejected one, remains in the pack.
"""
import json
from pathlib import Path
import shutil
import time
import uuid

import numpy as np
from scipy.spatial import cKDTree
import trimesh

from .bundle import atomic_json, bundle_checksums, file_sha256, verify_bundle, environment_signature
from .field import CaveField
from .pipeline import digest, mesh_digest
from .planning import NavigationSpace, certify_polyline
from .routes import build_routes
from .sensors import stereo_rgb_rig


def sample_requests(routes, branches, count=12, seed=0, safety=.55):
    """Deterministic, fixed-budget endpoint requests; no outcome-dependent resampling."""
    if isinstance(count, bool) or int(count) != count or count < 1:
        raise ValueError('Task count must be a positive integer')
    if isinstance(seed, bool) or int(seed) != seed or seed < 0:
        raise ValueError('Task seed must be a nonnegative integer')
    rng = np.random.default_rng(seed)
    names = [r['id'] for r in routes]
    points = [np.asarray(r['points']) for r in routes]
    pools = []
    for i, p in enumerate(points):
        indices = np.arange(max(4, int(len(p)*.15)), min(len(p)-4, int(len(p)*.85)))
        if i and len(points) > 1:
            others = cKDTree(np.concatenate([r for j, r in enumerate(points) if j != i]))
            indices = indices[others.query(p[indices])[0] > 2*safety]
        pools.append(indices)
    modes = ['main_to_main']
    if len(points) > 1:
        modes += ['main_to_branch', 'branch_to_main']
        if len(points) > 2:
            modes += ['branch_to_branch']
    requests = []
    for k in range(count):
        mode = modes[k % len(modes)]
        if mode == 'main_to_main':
            a = b = 0
        elif mode == 'main_to_branch':
            a, b = 0, int(rng.integers(1, len(points)))
        elif mode == 'branch_to_main':
            a, b = int(rng.integers(1, len(points))), 0
        else:
            a, b = map(int, rng.choice(np.arange(1, len(points)), 2, replace=False))
        item = {'id': f'task_{k:04d}', 'requested_class': mode,
                'start_route': names[a], 'goal_route': names[b],
                'start_route_is_loop': bool(a and 'rejoin_at' in branches[a-1]),
                'goal_route_is_loop': bool(b and 'rejoin_at' in branches[b-1]),
                'initial_yaw_radians': float(rng.uniform(-np.pi, np.pi))}
        if not len(pools[a]) or not len(pools[b]) or (a == b and len(pools[a]) < 2):
            item['request_error'] = 'no_unambiguous_interior_endpoint_pool'
        else:
            if a == b:
                n = len(pools[a])
                ia = int(rng.choice(pools[a][:max(1, n//3)]))
                ib = int(rng.choice(pools[b][max(1, 2*n//3):]))
            else:
                ia, ib = int(rng.choice(pools[a])), int(rng.choice(pools[b]))
            item.update(start_index=ia, goal_index=ib,
                        start=points[a][ia].tolist(), goal=points[b][ib].tolist())
        requests.append(item)
    return requests


def path_metrics(points, certificates, safety):
    p = np.asarray(points)
    distances = np.linalg.norm(np.diff(p, axis=0), axis=1)
    s = np.r_[0., np.cumsum(distances)]
    length = float(s[-1])
    straight = float(np.linalg.norm(p[-1]-p[0]))
    query = np.linspace(0, length, max(2, int(np.ceil(length/3))+1))
    coarse = np.column_stack([np.interp(query, s, p[:, i]) for i in range(3)])
    direction = np.diff(coarse, axis=0)
    direction /= np.maximum(np.linalg.norm(direction, axis=1, keepdims=True), 1e-9)
    turning = float(np.rad2deg(np.arccos(np.clip(np.sum(direction[:-1]*direction[1:], axis=1), -1, 1))).sum())
    lower = min(c['continuous_clearance_lower_bound'] for c in certificates.values())
    # Declared geometric bins; not calibrated against learned policy success.
    difficulty = ('hard' if lower/safety < 1.5 or length > 80 or turning > 150 else
                  'medium' if length > 35 or turning > 60 else 'easy')
    return {'path_length_m': length, 'endpoint_distance_m': straight,
            'path_length_over_endpoint_distance': length/max(straight, 1e-9),
            'continuous_clearance_lower_bound_m': lower, 'clearance_over_required_radius': lower/safety,
            'elevation_span_m': float(np.ptp(p[:, 2])),
            'heading_change_at_3m_sampling_degrees': turning, 'geometric_bin': difficulty,
            'bin_note': 'Fixed geometric heuristic; not empirical policy difficulty; path is clearance-weighted, not shortest Euclidean path.'}


def build_task_pack(source, output, count=12, seed=0, max_expansions=500000):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists() or output == source or source in output.parents or output in source.parents:
        raise ValueError('Task pack requires a new directory separate from its source')
    verify_bundle(source)
    spec = json.loads((source/'metadata/config.json').read_text(encoding='utf-8'))
    provenance = json.loads((source/'metadata/provenance.json').read_text())
    nav = json.loads((source/'navigation/centerline.json').read_text())['routes']
    safety = spec['robot']['radius']+spec['robot']['margin']
    requests = sample_requests(nav, spec['branches'], count, seed, safety)
    meshes = {}
    for kind in ['visual', 'collision']:
        data = np.load(source/kind/'mesh.npz')
        meshes[kind] = trimesh.Trimesh(data['vertices'], data['faces'], process=False)
        if not meshes[kind].is_watertight:
            raise ValueError('Multi-task certification currently requires a closed reference bundle')
    began = time.perf_counter()
    # Old bundles did not persist occupancy. Replay it once, requiring the
    # reconstructed collision mesh digest to match the actual immutable source.
    field = CaveField(spec, build_routes(spec), provenance['seed'])
    replay, grid, origin = field.mesh(spec['mesh']['collision_voxel'])
    if mesh_digest(replay) != provenance['collision_mesh_sha256']:
        raise ValueError('Occupancy replay differs from source mesh; refusing stale geometry')
    space = NavigationSpace(grid, origin, spec['mesh']['collision_voxel'], safety)
    setup_seconds = time.perf_counter()-began
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_name('.'+output.name+'.building-'+uuid.uuid4().hex[:8])
    temp.mkdir()
    for name in ['tasks', 'metadata', 'navigation']:
        (temp/name).mkdir()
    for name in ['visual', 'collision', 'materials']:
        shutil.copytree(source/name, temp/name)
    shutil.copy2(source/'navigation/centerline.json', temp/'navigation/centerline.json')
    shutil.copy2(source/'metadata/config.json', temp/'metadata/config.json')
    np.savez_compressed(temp/'navigation/occupancy.npz', free=grid > 0, origin=origin,
                        voxel=spec['mesh']['collision_voxel'])
    results, episodes = [], []
    junctions = json.loads((source/'navigation/junction_graph.json').read_text())['nodes']
    junctions = [j for j in junctions if j.get('degree', 0) >= 3]
    for request in requests:
        if request.get('request_error'):
            result = {'status': 'FAIL', 'reason': request['request_error']}
        else:
            result = space.plan(meshes['collision'], request['start'], request['goal'], max_expansions)
            if result['status'] == 'PASS':
                result['visual_certificate'] = certify_polyline(meshes['visual'], result['points'], safety)
                if result['visual_certificate']['status'] != 'PASS':
                    result.update(status='FAIL', reason='candidate_failed_visual_mesh_certificate')
            if result['status'] == 'PASS':
                certificates = {kind: result[kind+'_certificate'] for kind in meshes}
                result['metrics'] = path_metrics(result['points'], certificates, safety)
                witness_tree = cKDTree(result['points'])
                result['metrics']['nearby_semantic_junction_ids'] = [j['id'] for j in junctions
                    if witness_tree.query(j['position'])[0] < 2.]
                result['metrics']['junction_note'] = 'Semantic nodes within 2 m of the witness; not recovered free-space topology or decision count.'
                yaw = request['initial_yaw_radians']
                episodes.append({'id': request['id'], 'start': {'position_m': request['start'],
                    'orientation_wxyz': [float(np.cos(yaw/2)), 0., 0., float(np.sin(yaw/2))]},
                    'goal': {'position_m': request['goal'], 'tolerance_m': .5},
                    'geometric_bin': result['metrics']['geometric_bin']})
        record = {'request': request, 'planning': result}
        atomic_json(temp/'tasks'/f"{request['id']}.json", record)
        results.append({'id': request['id'], 'class': request['requested_class'], 'status': result['status'],
                        'reason': result.get('reason'), 'metrics': result.get('metrics')})
        print(request['id'], request['requested_class'], result['status'], flush=True)
    atomic_json(temp/'episodes.json', {'schema_version': 1, 'episodes': episodes})
    contract = {'schema_version': 1, 'units': 'metres', 'up_axis': 'Z', 'handedness': 'right',
                'orientation_order': 'wxyz', 'robot_envelope': spec['robot'],
                'visual': 'visual/cave_visual.obj', 'collision': 'collision/cave_collision.obj',
                'episodes': 'episodes.json', 'surface_type': 'closed reference cavity, inward wall normals',
                'policy_inputs': {'status': 'stereo RGB sensors selected; goal-conditioning and action interface pending',
                    'goal_condition': 'UNSPECIFIED: task goals are environment metadata, not automatically actor observations',
                    'sensors': ['rgb_left', 'rgb_right'], 'rig': 'stereo_rig.json'},
                'privileged_artifacts': ['navigation/', 'tasks/', 'metadata/'],
                'privileged_rule': 'Not policy observations. Witness paths/occupancy/graphs are for validation or explicitly declared supervision only.',
                'limitations': ['Spherical static envelope only; no dynamics certificate.',
                    'No claim that a goal-unconditioned reactive policy can solve ambiguous junctions.',
                    'Appearance/sensor/dynamics randomization belong to a separately logged environment layer.']}
    atomic_json(temp/'training_contract.json', contract)
    atomic_json(temp/'stereo_rig.json', stereo_rgb_rig())
    manifest = {'schema_version': 1, 'artifact_type': 'verified_multi_task_pack',
        'status': 'COMPLETE' if len(episodes) == count else 'PARTIAL',
        'source_name': spec['name'], 'source_split': spec['split'], 'scene_seed': provenance['seed'],
        'source_checksums_sha256': file_sha256(source/'metadata/checksums.json'),
        'source_mesh_files': {k: file_sha256(source/k/'mesh.npz') for k in meshes},
        'task_seed': seed, 'requested': count, 'passed': len(episodes), 'failed': count-len(episodes),
        'all_requests': results, 'occupancy_replay_verified': True, 'setup_seconds': setup_seconds,
        'total_seconds': time.perf_counter()-began, 'environment': environment_signature(),
        'task_rules': 'Balanced requested endpoint classes; fixed budget; failures retained, no silent replacement.',
        'split_rule': 'Tasks inherit the source cave split; do not randomly divide episodes from one cave across train/test.'}
    manifest['semantic_digest'] = digest({'requests': requests,
        'paths': [json.loads((temp/'tasks'/f"{r['id']}.json").read_text())['planning'].get('points') for r in results]})
    atomic_json(temp/'metadata/manifest.json', manifest)
    atomic_json(temp/'metadata/checksums.json', bundle_checksums(temp))
    temp.rename(output)
    return manifest


def load_task_pack(folder):
    """Validate portable file inventory and reset data; returns no privileged paths."""
    folder = Path(folder)
    checks = json.loads((folder/'metadata/checksums.json').read_text())
    if checks != bundle_checksums(folder):
        raise ValueError('Task pack integrity mismatch')
    contract = json.loads((folder/'training_contract.json').read_text())
    if (contract['units'], contract['up_axis'], contract['orientation_order']) != ('metres', 'Z', 'wxyz'):
        raise ValueError('Unsupported training coordinate contract')
    episodes = json.loads((folder/'episodes.json').read_text())['episodes']
    safety = contract['robot_envelope']['radius'] + contract['robot_envelope']['margin']
    if len({e['id'] for e in episodes}) != len(episodes):
        raise ValueError('Duplicate episode ids')
    for episode in episodes:
        if not episode['id'].startswith('task_') or not episode['id'][5:].isdigit():
            raise ValueError('Invalid episode id')
        q = np.asarray(episode['start']['orientation_wxyz'])
        if q.shape != (4,) or not np.isfinite(q).all() or abs(np.linalg.norm(q)-1) > 1e-6:
            raise ValueError('Invalid reset orientation')
        for p in [episode['start']['position_m'], episode['goal']['position_m']]:
            if np.asarray(p).shape != (3,) or not np.isfinite(p).all():
                raise ValueError('Invalid reset position')
        task = json.loads((folder/'tasks'/f"{episode['id']}.json").read_text())
        plan = task['planning']
        if plan['status'] != 'PASS' or not np.allclose(plan['start'], episode['start']['position_m']) or not np.allclose(plan['goal'], episode['goal']['position_m']):
            raise ValueError('Episode differs from its validated task')
        for kind in ['visual', 'collision']:
            certificate = plan[kind+'_certificate']
            if (certificate['status'] != 'PASS' or not certificate['samples_inside']
                    or certificate['required_radius'] != safety
                    or not np.isfinite(certificate['continuous_clearance_lower_bound'])
                    or certificate['continuous_clearance_lower_bound'] <= safety):
                raise ValueError('Missing dual-mesh certificate')
    return contract, episodes
