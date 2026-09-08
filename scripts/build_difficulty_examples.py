"""Generate one deterministic, open cave per geometric difficulty tier."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cave_composer.pipeline import generate
from cave_composer.portals import export_portals
from cave_composer.routes import build_routes
from cave_composer.spec import load_spec
from cave_composer.bundle import verify_bundle, verify_portal_export


def specifications():
    common = {'split': 'difficulty_examples', 'material': {'style': 'sandstone', 'seed': 83500, 'roughness': .87}}
    easy = {**common, 'name': 'easy_01',
            'description': 'Wide passage, gentle paired bends, level floor, no branches.',
            'corridor': {'width': 6., 'height': 4.8, 'variation': .10},
            'geology': {'amplitude': .22, 'strata': .10, 'formations': 4},
            'route': [{'straight': 14}, {'turn': 30, 'radius': 8}, {'straight': 14},
                      {'turn': -30, 'radius': 8}, {'straight': 14}]}
    medium = {**common, 'name': 'medium_01',
              'description': 'Moderate width, four bends, gentle vertical changes and one chamber.',
              'corridor': {'width': 4.5, 'height': 3.8, 'variation': .16},
              'geology': {'amplitude': .30, 'strata': .14, 'formations': 10},
              'route': [{'straight': 14}, {'turn': 60, 'radius': 7}, {'straight': 12, 'slope': -6},
                        {'turn': -60, 'radius': 7}, {'straight': 12},
                        {'turn': -45, 'radius': 7}, {'straight': 12, 'slope': 4},
                        {'turn': 45, 'radius': 7}, {'straight': 14}],
              'chambers': [{'at': .50, 'radii': [4., 3.8, 3.2], 'lobes': 4}]}
    hard = {**common, 'name': 'hard_01',
            'description': 'Narrow passage, four right-angle bends, two dead-end branches and a bottleneck.',
            'corridor': {'width': 3.0, 'height': 3.3, 'variation': .18, 'section': 'asymmetric'},
            'geology': {'amplitude': .40, 'strata': .16, 'formations': 20},
            'route': [{'straight': 18}, {'turn': 90, 'radius': 5}, {'straight': 14, 'slope': -14},
                      {'turn': -90, 'radius': 5}, {'straight': 18},
                      {'turn': -90, 'radius': 5}, {'straight': 14, 'slope': 10},
                      {'turn': 90, 'radius': 5}, {'straight': 18}],
            'bottlenecks': [{'at': .5, 'length': 5, 'width': 2.8, 'height': 3.0}]}
    # Anchor branches on straight passages, away from terminal clipping planes.
    route = build_routes(load_spec(hard))[0]
    anchors = []
    for command in [0, 4]:
        event = route['events'][command]
        index = round((event['start_index'] + event['end_index']) / 2)
        anchors.append(index / (len(route['points']) - 1))
    hard['branches'] = [{'at': anchors[0], 'heading': -90, 'route': [{'straight': 12}]},
                        {'at': anchors[1], 'heading': 90, 'route': [{'straight': 12}]}]
    return {k: load_spec(v) for k, v in [('easy', easy), ('medium', medium), ('hard', hard)]}


def main(work, blender):
    blender = shutil.which(blender or os.environ.get('BLENDER_PATH') or 'blender')
    if not blender:
        raise ValueError('Blender not found; use --blender or BLENDER_PATH')
    work = Path(work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    summaries = []
    for i, (tier, config) in enumerate(specifications().items()):
        source = work / tier / 'reference'
        opened = work / tier / 'open'
        seed = 83001 + i
        if source.exists():
            run = verify_bundle(source)
            saved = json.loads((source / 'metadata/config.json').read_text())
            if saved != config or run['seed'] != seed:
                raise ValueError('Existing configuration mismatch')
        else:
            print(tier, 'generating', flush=True)
            generate(config, seed, source, render=False)
        if not opened.exists():
            print(tier, 'opening portals', flush=True)
            export_portals(source, opened)
        verify_portal_export(opened, source)
        with (opened / 'metadata/intersection_audit.log').open('w', encoding='utf-8') as log:
            subprocess.run([blender, '--background', '--python-exit-code', '1', '--python',
                            str(Path(__file__).resolve().parents[1] / 'cave_composer/blender_audit.py'),
                            '--', '--scene', str(opened)], stdout=log, stderr=subprocess.STDOUT, check=True)
        report = json.loads((opened / 'metadata/portal_validation.json').read_text())
        routes = build_routes(config)
        entry = {'difficulty': tier, 'seed': seed, 'source': str(source), 'open': str(opened),
                 'main_route_length_m': float(routes[0]['s'][-1]),
                 'total_route_length_m': float(sum(r['s'][-1] for r in routes)),
                 'nominal_width_m': config['corridor']['width'], 'nominal_height_m': config['corridor']['height'],
                 'turn_angles_deg': [c['turn'] for c in config['route'] if 'turn' in c],
                 'max_absolute_slope_deg': max(abs(c.get('slope', 0)) for c in config['route']),
                 'branches': len(config['branches']), 'chambers': len(config['chambers']),
                 'bottlenecks': len(config['bottlenecks']),
                 'robot_required_radius_m': config['robot']['radius'] + config['robot']['margin'],
                 'path_clearance_lower_bound_m': min(v['crossing_certificate']['continuous_clearance_lower_bound']
                                                     for v in report['meshes'].values()),
                 'difficulty_scope': 'Designed geometric tiers, not measured navigation-policy difficulty'}
        summaries.append(entry)
        (work / 'summary.json').write_text(json.dumps(summaries, indent=2), encoding='utf-8')
        print(tier, 'PASS', entry['path_clearance_lower_bound_m'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', default='outputs/difficulty_examples_v01')
    parser.add_argument('--blender', help='Executable path; defaults to BLENDER_PATH or PATH')
    args = parser.parse_args()
    main(args.work, args.blender)
