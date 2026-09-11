"""Exercise a source checkout without external scans, an RL stack or old outputs.

Writes a fresh report directory. Archived evidence and delivered assets are read-only.
Use --blender for texture baking. --archives and --all-assets require local data.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import yaml
from cave_composer.bundle import atomic_json, bundle_checksums, file_sha256, verify_bundle, verify_portal_export
from cave_composer.tasks import load_task_pack
from scripts.check_c2_release_v02 import check as check_release
from scripts.verify_textured_exports import verify as verify_exports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--blender', help='Optional Blender executable; enables real texture baking')
    parser.add_argument('--all-assets', action='store_true')
    parser.add_argument('--archives', action='store_true',
                        help='Verify locally retained historical evidence and frozen assets; not included in Git')
    parser.add_argument('--paper', action='store_true', help='Compile using installed pdfLaTeX/BibTeX')
    args = parser.parse_args()
    os.chdir(ROOT)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {'status': 'RUNNING', 'checks': {}, 'commands': [],
              'scope': 'Release reproducibility and geometric checks; no training or policy evaluation'}
    env = dict(os.environ, PYTHONNOUSERSITE='1', PYTHONUTF8='1')
    env.pop('PYTHONPATH', None)

    def run(name, command):
        start = time.perf_counter()
        with (output / (name + '.log')).open('wb') as log:
            result = subprocess.run([str(x) for x in command], cwd=ROOT, env=env,
                                    stdout=log, stderr=subprocess.STDOUT)
        report['commands'].append({'name': name, 'command': [str(x) for x in command],
                                   'returncode': result.returncode, 'seconds': time.perf_counter()-start})
        if result.returncode:
            raise RuntimeError(f'{name} failed; see {output / (name + ".log")}')
        print(name, 'PASS', flush=True)

    try:
        if args.archives:
            ledger = yaml.safe_load((ROOT / 'overleaf/CLAIM_EVIDENCE.yaml').read_text(encoding='utf-8'))
            artifacts = [item for c in ledger['claims'] for item in c.get('raw_artifacts', [])]
            required = [ROOT / item['path'] for item in artifacts]
            required += [ROOT/'exports/cavern_pretraining_v02/manifest.json',
                         ROOT/'outputs/c1_pilot_v02/summary.json']
            missing = [str(p.relative_to(ROOT)) for p in required if not p.is_file()]
            if missing:
                raise FileNotFoundError('--archives requires locally retained original data, absent from this source checkout: '
                                        + ', '.join(missing))
            for item in artifacts:
                if file_sha256(ROOT / item['path']) != item['sha256']:
                    raise ValueError('Recorded claim artifact changed: ' + item['path'])
            report['checks']['claim_artifact_bindings'] = len(artifacts)
            report['checks']['frozen_release'] = check_release(ROOT / 'exports/cavern_pretraining_v02')
            print('Archived evidence and 8-scene release PASS', flush=True)
        else:
            report['checks']['claim_artifact_bindings'] = 'NOT_RUN: historical data is local-only; requires --archives'
            report['checks']['frozen_release'] = 'NOT_RUN: historical data is local-only; requires --archives'

        if args.all_assets and not (ROOT/'exports/caves_difficulty_v01/batch_manifest.json').is_file():
            raise FileNotFoundError('--all-assets requires a locally generated exports/caves_difficulty_v01 collection')

        config = ROOT / 'configs/morphology_v02/after.json'
        for name in ['scene_a', 'scene_b']:
            run(name, [sys.executable, ROOT / 'generate.py', '--config', config,
                       '--seed', '97001', '--output', output / name])
            verify_bundle(output / name)
        for kind in ['visual', 'collision']:
            with np.load(output / 'scene_a' / kind / 'mesh.npz') as a, np.load(output / 'scene_b' / kind / 'mesh.npz') as b:
                if any(not np.array_equal(a[key], b[key]) for key in ['vertices', 'faces']):
                    raise ValueError('Same-seed mesh arrays differ: ' + kind)
        if file_sha256(output/'scene_a/materials/rock_albedo.png') != file_sha256(output/'scene_b/materials/rock_albedo.png'):
            raise ValueError('Same-seed materials differ')
        report['checks']['same_seed_mesh_and_material'] = 'PASS'
        run('tasks', [sys.executable, ROOT/'scripts/build_navigation_tasks.py',
                     '--scene', output/'scene_a', '--output', output/'tasks', '--count', '3', '--seed', '88200'])
        contract, tasks = load_task_pack(output/'tasks')
        if not tasks:
            raise ValueError('No accepted task in the reproducibility case')
        report['checks']['sampled_tasks'] = {'requested': 3, 'accepted': len(tasks)}
        run('portals', [sys.executable, ROOT/'scripts/export_portals.py', '--scene', output/'scene_a', '--output', output/'open'])
        verify_portal_export(output/'open')
        report['checks']['portal_export'] = 'PASS'

        if args.blender:
            run('blender_audit', [args.blender, '--background', '--python-exit-code', '1', '--python',
                                 ROOT/'cave_composer/blender_audit.py', '--', '--scene', output/'open'])
            atomic_json(output/'open/metadata/checksums.json', bundle_checksums(output/'open'))
            run('portable_export', [args.blender, '--background', '--python-exit-code', '1', '--python',
                                   ROOT/'scripts/export_textured_cave.py', '--', '--scene', output/'open',
                                   '--output', output/'portable', '--name', 'cave', '--resolution', '1024'])
            report['checks']['new_textured_glb_obj'] = verify_exports(output, output/'portable_checks.json',
                [{'difficulty': 'reproduction', 'folder': 'portable', 'name': 'cave'}])
        else:
            report['checks']['new_textured_glb_obj'] = 'NOT_RUN: supply --blender'
        if args.all_assets:
            report['checks']['difficulty_assets'] = len(verify_exports(ROOT/'exports/caves_difficulty_v01', output/'30_assets.json'))
        else:
            report['checks']['difficulty_assets'] = 'NOT_RUN: supply --all-assets'
        if args.archives:
            run('analysis', [sys.executable, ROOT/'scripts/analyze_c1_pilot_v02.py', '--output', output/'analysis'])
            original = json.loads((ROOT/'outputs/c1_pilot_v02/summary.json').read_text(encoding='utf-8'))
            reproduced = json.loads((output/'analysis/summary.json').read_text(encoding='utf-8'))
            if any(original[key] != reproduced[key] for key in ['rows', 'groups']):
                raise ValueError('Pilot summary differs from the archived raw results')
            if (output/'analysis/generator.tex').read_text(encoding='utf-8') != (ROOT/'overleaf/tables/generator.tex').read_text(encoding='utf-8'):
                raise ValueError('Rebuilt table differs from the manuscript')
            report['checks']['pilot_analysis_and_table'] = 'PASS'
        else:
            report['checks']['pilot_analysis_and_table'] = 'NOT_RUN: historical data is local-only; requires --archives'
        if args.paper:
            run('paper', [sys.executable, ROOT/'scripts/build_cavern_paper.py'])
            log = (ROOT/'overleaf/build/main.log').read_text(encoding='utf-8', errors='replace')
            if 'undefined' in log or 'Overfull' in log:
                raise ValueError('Paper has unresolved references or overfull boxes')
            report['checks']['paper'] = 'PASS'
        else:
            report['checks']['paper'] = 'NOT_RUN: supply --paper'
        report['status'] = 'PASS'
    except Exception as exc:
        report.update(status='FAIL', error=repr(exc))
        raise
    finally:
        atomic_json(output/'verification.json', report)
    print(output/'verification.json')


if __name__ == '__main__':
    main()
