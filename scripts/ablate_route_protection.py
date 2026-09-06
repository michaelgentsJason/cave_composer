"""Paired collision-mesh stress test of route protection, retaining all outcomes.

An experimental intervention changes only CaveField.protected_radius after
initialization. No production setting disables protection or mesh validation.
"""
import argparse
import json
from pathlib import Path
import sys
import time
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cave_composer.spec import load_spec
from cave_composer.routes import build_routes, navigation_graph
from cave_composer.field import CaveField
from cave_composer.validation import validate
from cave_composer.planning import plan_navigation
from cave_composer.bundle import atomic_json, environment_signature, file_sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='outputs/protection_ablation_v03')
    parser.add_argument('--pairs', type=int, default=8)
    parser.add_argument('--base-seed', type=int, default=41000)
    args = parser.parse_args()
    root = Path(args.output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    records = []
    for i in range(args.pairs):
        seed = args.base_seed + i
        spec = load_spec({'name': f'protection_stress_{seed}',
                          'route': [{'straight': 14}, {'turn': 65, 'radius': 5.5}, {'straight': 13}],
                          'corridor': {'width': 3.0, 'height': 3.0, 'variation': .2,
                                       'section': ['fracture', 'asymmetric', 'irregular', 'flattened'][i % 4]},
                          'geology': {'amplitude': .65 if i < args.pairs // 2 else .9,
                                      'strata': .18, 'formations': 25},
                          'mesh': {'visual_voxel': .34, 'collision_voxel': .34}})
        routes = build_routes(spec)
        graph = navigation_graph(routes, [])
        for enabled in (False, True):
            folder = root / f'pair_{i:03d}' / ('protected' if enabled else 'unprotected')
            folder.mkdir(parents=True)
            record = {'pair': i, 'seed': seed, 'protection': enabled,
                      'path': folder.relative_to(root).as_posix(),
                      'design_route_valid': False, 'independent_path_pass': False}
            start = time.perf_counter()
            field = CaveField(spec, routes, seed)
            original = field.protected_radius
            if not enabled:
                field.protected_radius = 0.
            atomic_json(folder / 'request.json', {'spec': spec, 'seed': seed,
                        'intervention': {'protected_radius_metres': field.protected_radius,
                                         'production_radius_metres': original},
                        'scope': 'collision-resolution geometry only; paired configuration and random phases'})
            try:
                mesh, grid, origin = field.mesh(.34)
                np.savez_compressed(folder / 'collision_mesh.npz', vertices=mesh.vertices, faces=mesh.faces)
                mesh.export(folder / 'collision.obj')
                report, _ = validate(spec, routes, graph, field, mesh, mesh, grid, origin)
                atomic_json(folder / 'validation.json', report)
                route_keys = ['collision_route_clearance', 'collision_route_inside', 'robot_space_route_connected']
                record['design_route_valid'] = all(report['checks'][key] for key in route_keys)
                record['all_checks_valid'] = report['status'] == 'VALID'
                record['route_clearance_lower_bound'] = report['mesh']['collision']['continuous_polyline_clearance_lower_bound']
                record['failed_checks'] = [key for key, value in report['checks'].items() if not value]
                main = routes[0]['points']
                plan = plan_navigation(mesh, grid, origin, .34, main[6], main[-7], .55)
                atomic_json(folder / 'planned_path.json', plan)
                record['independent_path_pass'] = plan['status'] == 'PASS'
                record['planning_reason'] = plan.get('reason')
            except Exception as exc:
                record['error'] = f'{type(exc).__name__}: {exc}'
            record['seconds'] = time.perf_counter() - start
            atomic_json(folder / 'outcome.json', record)
            records.append(record)
            result = {'scope': 'Small paired stress test, not representative cave failure rates, PLUME comparison or policy training.',
                      'pairs_requested': args.pairs, 'base_seed': args.base_seed,
                      'environment': environment_signature(), 'records': records}
            atomic_json(root / 'results.json', result)
            print(json.dumps(record), flush=True)
    summary = {}
    for enabled in (False, True):
        group = [r for r in records if r['protection'] == enabled]
        summary['protected' if enabled else 'unprotected'] = {
            'requested': len(group), 'design_route_valid': sum(r['design_route_valid'] for r in group),
            'independent_path_pass': sum(r['independent_path_pass'] for r in group),
            'generation_errors': sum('error' in r for r in group)}
    result['summary'] = summary
    atomic_json(root / 'results.json', result)
    atomic_json(root / 'checksums.json', {p.relative_to(root).as_posix(): file_sha256(p)
                for p in sorted(root.rglob('*')) if p.is_file() and p.name != 'checksums.json'})


if __name__ == '__main__':
    main()
