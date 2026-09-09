"""Resume a textured, portal-checked difficulty collection without replacing old assets."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cave_composer.bundle import atomic_json, verify_bundle, verify_portal_export
from cave_composer.pipeline import generate
from cave_composer.portals import export_portals
from cave_composer.routes import build_routes
from cave_composer.spec import load_spec
from scripts.build_difficulty_examples import specifications
from scripts.verify_textured_exports import verify
from scripts.asset_gallery import write_gallery
from scripts.render_asset_overviews import render as render_overview

REPO = Path(__file__).resolve().parents[1]
TIERS = ['easy', 'medium', 'hard']


def variant(tier, index, attempt=0):
    seed = 940000 + TIERS.index(tier) * 10000 + index * 10 + attempt
    rng = np.random.default_rng(seed)
    spec = deepcopy(specifications()[tier])
    spec.update(name=f'{tier}_{index:03d}', split='difficulty_asset_collection')
    spec['material']['seed'] = seed + 100000
    ranges = {'easy': ((5.8, 7.0), (4.5, 5.4), (22, 38), (8, 10)),
              'medium': ((4.3, 5.0), (3.7, 4.3), (45, 65), (6.5, 8)),
              'hard': ((3.0, 3.35), (3.15, 3.6), (78, 92), (5, 6))}
    width, height, angles, radii = ranges[tier]
    spec['corridor']['width'] = round(float(rng.uniform(*width)), 3)
    spec['corridor']['height'] = round(float(rng.uniform(*height)), 3)
    spec['corridor']['section'] = str(rng.choice(['irregular', 'oval', 'asymmetric']))
    mirror = -1 if index % 2 else 1
    angle = round(float(rng.uniform(*angles)), 2)
    radius = round(float(rng.uniform(*radii)), 2)
    for command in spec['route']:
        if 'straight' in command:
            command['straight'] = round(command['straight'] * float(rng.uniform(.90, 1.20)), 2)
        if 'turn' in command:
            command['turn'] = float(np.sign(command['turn'])) * mirror * angle
            command['radius'] = radius
        if 'slope' in command:
            command['slope'] = round(command['slope'] * float(rng.uniform(.8, 1.1)), 2)
    spec['geology']['amplitude'] = round(spec['geology']['amplitude'] * float(rng.uniform(.9, 1.08)), 3)
    if tier == 'medium':
        spec['chambers'][0]['radii'] = [round(v * float(rng.uniform(.95, 1.15)), 2)
                                        for v in spec['chambers'][0]['radii']]
    if tier == 'hard':
        route = build_routes(load_spec(spec))[0]
        for branch, command_index in zip(spec['branches'], [0, 4]):
            event = route['events'][command_index]
            point_index = round((event['start_index'] + event['end_index']) / 2)
            branch['at'] = point_index / (len(route['points']) - 1)
            branch['heading'] *= mirror
            branch['route'][0]['straight'] = round(float(rng.uniform(10, 14)), 2)
    return load_spec(spec), seed


def blender_run(blender, script, args, log):
    with log.open('w', encoding='utf-8') as stream:
        subprocess.run([str(blender), '--background', '--threads', '6', '--python-exit-code', '1',
                        '--python', str(REPO / script), '--', *map(str, args)],
                       stdout=stream, stderr=subprocess.STDOUT, check=True)


def publish_catalog(root, assets, targets, failures):
    counts = {tier: sum(a['difficulty'] == tier for a in assets) for tier in TIERS}
    manifest = {'schema_version': 1, 'status': 'COMPLETE' if counts == targets else 'RUNNING',
                'counts': counts, 'targets': targets, 'assets': assets, 'failed_attempts': failures,
                'difficulty_scope': 'Designed geometric tiers, not calibrated policy difficulty'}
    atomic_json(root / 'batch_manifest.json', manifest)
    write_gallery(root, assets, targets)


def main(args):
    root, work = Path(args.root).resolve(), Path(args.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    root.mkdir(parents=True, exist_ok=True)
    backup = work / 'original_catalog'
    backup.mkdir(exist_ok=True)
    for name in ['README.md', 'index.html', 'checksums.json', 'verification.json']:
        if (root / name).exists() and not (backup / name).exists():
            shutil.copy2(root / name, backup / name)
    targets = dict(zip(TIERS, [args.easy, args.medium, args.hard]))
    prior = json.loads((root / 'batch_manifest.json').read_text()) if (root / 'batch_manifest.json').exists() else {}
    assets, failures = prior.get('assets', []), prior.get('failed_attempts', [])
    for tier in TIERS:
        if any(a['difficulty'] == tier and a['index'] == 1 for a in assets):
            continue
        entry = {'difficulty': tier, 'folder': tier, 'name': f'cave_{tier}', 'index': 1}
        verified = verify(root, entries=[entry])[0]
        meta = json.loads((root / tier / 'metadata.json').read_text())
        assets.append({**meta, **entry, 'verification': verified, 'reused_existing': True})
    publish_catalog(root, assets, targets, failures)
    for tier in TIERS:
        for index in range(2, targets[tier] + 1):
            if any(a['difficulty'] == tier and a['index'] == index for a in assets):
                continue
            name = f'cave_{tier}_{index:03d}'
            final = root / tier / f'scene_{index:03d}'
            if final.exists():
                entry = json.loads((final / 'metadata.json').read_text())
                entry['verification'] = verify(root, entries=[entry])[0]
                assets.append(entry)
                publish_catalog(root, assets, targets, failures)
                continue
            for attempt in range(3):
                run_dir = work / tier / f'scene_{index:03d}_attempt_{attempt}'
                run_dir.mkdir(parents=True, exist_ok=True)
                config, seed = variant(tier, index, attempt)
                reference, opened, staging = [run_dir / p for p in ['reference', 'open', 'textured']]
                try:
                    print(f'{name} attempt={attempt} seed={seed} GENERATE', flush=True)
                    if reference.exists():
                        run = verify_bundle(reference)
                        if run['seed'] != seed or json.loads((reference / 'metadata/config.json').read_text()) != config:
                            raise ValueError('Resume configuration mismatch')
                    else:
                        generate(config, seed, reference, render=False)
                    if not opened.exists():
                        export_portals(reference, opened)
                    verify_portal_export(opened, reference)
                    blender_run(args.blender, 'cave_composer/blender_audit.py', ['--scene', opened], run_dir / 'audit.log')
                    print(name, 'BAKE AND EXPORT', flush=True)
                    if not (staging / 'export_verification.json').exists():
                        blender_run(args.blender, 'scripts/export_textured_cave.py',
                                    ['--scene', opened, '--output', staging, '--name', name, '--resolution', 4096],
                                    run_dir / 'export.log')
                    entry = {'difficulty': tier, 'index': index, 'name': name,
                             'folder': final.relative_to(root).as_posix()}
                    verified = verify(run_dir, entries=[{**entry, 'folder': 'textured'}])[0]
                    verified['folder'] = entry['folder']
                    routes = build_routes(config)
                    meta = {**entry, 'seed': seed, 'source': str(reference), 'open': str(opened),
                            'main_route_length_m': float(routes[0]['s'][-1]),
                            'total_route_length_m': float(sum(r['s'][-1] for r in routes)),
                            'nominal_width_m': config['corridor']['width'], 'nominal_height_m': config['corridor']['height'],
                            'turn_angles_deg': [c['turn'] for c in config['route'] if 'turn' in c],
                            'max_absolute_slope_deg': max(abs(c.get('slope', 0)) for c in config['route']),
                            'branches': len(config['branches']), 'chambers': len(config['chambers']),
                            'bottlenecks': len(config['bottlenecks']), 'robot_required_radius_m': .55,
                            'path_clearance_lower_bound_m': min(f['crossing_certificate']['continuous_clearance_lower_bound']
                                                                for f in verified['formats'].values()),
                            'difficulty_scope': 'Designed geometric tiers, not measured policy difficulty',
                            'verification': verified, 'reused_existing': False}
                    atomic_json(staging / 'metadata.json', meta)
                    atomic_json(staging / 'portable_verification.json', verified)
                    render_overview(staging)
                    staging.rename(final)
                    assets.append(meta)
                    assets.sort(key=lambda a: (TIERS.index(a['difficulty']), a['index']))
                    publish_catalog(root, assets, targets, failures)
                    print(name, f'COMPLETE {len(assets)}/{sum(targets.values())}', flush=True)
                    break
                except Exception as exc:
                    error = {'difficulty': tier, 'index': index, 'attempt': attempt, 'seed': seed,
                             'error': f'{type(exc).__name__}: {exc}', 'diagnostics': str(run_dir)}
                    failures.append(error)
                    atomic_json(run_dir / 'failure.json', error)
                    publish_catalog(root, assets, targets, failures)
                    print('FAILED', error, flush=True)
            else:
                raise RuntimeError(f'{name}: all attempts failed; diagnostics retained')
    atomic_json(root / 'verification.json', [a['verification'] for a in assets])
    old_readme = (backup / 'README.md').read_text(encoding='utf-8')
    note = '# Difficulty asset collection\n\n'
    note += f'Current totals: easy {targets["easy"]}, medium {targets["medium"]}, hard {targets["hard"]}. '
    note += 'Includes the three original assets, preserved at their original paths.\n\n'
    note += '[Open the complete gallery](index.html) · [Asset manifest](batch_manifest.json) · [Verification](verification.json)\n\n'
    note += 'New assets: `<tier>/scene_002/`, `scene_003/`, etc. Each contains GLB, OBJ, MTL, 4K color/normal textures, a GLB reimport preview, navigation paths, configuration and checks. Move the whole scene directory when using OBJ.\n\n'
    note += 'All assets have two physical openings and a checked crossing path for a 0.55 m spherical envelope. Difficulty is assigned by geometric design, not measured policy success. Failed generation attempts remain in the manifest; this is an accepted asset collection, not an unbiased generation success-rate benchmark.\n\n'
    note += 'The old sibling ZIP is the original three-asset archive; use this folder for the expanded collection.\n\n'
    note += '## Original three-asset documentation\n\n' + old_readme
    (root / 'README.md').write_text(note, encoding='utf-8')
    checksums = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(root.rglob('*')) if p.is_file() and p != root / 'checksums.json'}
    atomic_json(root / 'checksums.json', checksums)
    print('COLLECTION COMPLETE', targets, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='exports/caves_difficulty_v01')
    parser.add_argument('--work', default='outputs/difficulty_expansion_v01')
    parser.add_argument('--blender', default='D:/Blender/blender.exe')
    parser.add_argument('--easy', type=int, default=15)
    parser.add_argument('--medium', type=int, default=10)
    parser.add_argument('--hard', type=int, default=5)
    main(parser.parse_args())
