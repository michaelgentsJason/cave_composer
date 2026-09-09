"""Build and validate diverse medium/hard assets, then swap the gallery atomically."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import traceback

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cave_composer.bundle import atomic_json, verify_bundle, verify_portal_export
from cave_composer.organic_sampling import sample_organic_config, PROFILES
from cave_composer.pipeline import generate
from cave_composer.portals import export_portals
from cave_composer.routes import build_routes, navigation_graph
from scripts.expand_difficulty_exports import blender_run
from scripts.verify_textured_exports import verify
from scripts.render_asset_overviews import render as render_overview
from scripts.asset_gallery import write_gallery

REPO = Path(__file__).resolve().parents[1]


def safe_rename(source, destination):
    source, destination = source.resolve(), destination.resolve()
    for path in (source, destination):
        path.relative_to(REPO)
        if path == REPO:
            raise ValueError('Cannot move the repository root')
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    print('MOVE', str(source), '->', str(destination), flush=True)
    source.rename(destination)


def checksum_tree(root):
    atomic_json(root / 'checksums.json', {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                        for p in sorted(root.rglob('*')) if p.is_file() and p != root/'checksums.json'})


def main(args):
    root, work = Path(args.root).resolve(), Path(args.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    state_path = work / 'run_manifest.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {'status':'RUNNING','assets':[],'failed_attempts':[]}
    if state['status'] == 'COMPLETE':
        print('Already complete:', root)
        return
    collection = work / 'collection'
    collection.mkdir(exist_ok=True)
    for tier, profiles in PROFILES.items():
        for index in range(1, len(profiles)+1):
            if any(a['difficulty']==tier and a['index']==index for a in state['assets']):
                continue
            final = collection / tier / f'scene_{index:03d}'
            name = f'cave_{tier}_{index:03d}'
            if final.exists():
                meta = json.loads((final/'metadata.json').read_text())
                verify(collection, entries=[meta])
                state['assets'].append(meta)
                atomic_json(state_path, state)
                continue
            for attempt in range(args.attempts):
                seed = (1070000 if tier=='medium' else 1080000)+index*100+attempt
                run = work/tier/f'scene_{index:03d}_attempt_{attempt}'
                if (run/'failure.json').exists():
                    failure=json.loads((run/'failure.json').read_text())
                    recoverable=any(t in failure['error'] for t in ['entrance and exit loops','wall/rock component structure'])
                    if recoverable and (run/'reference/metadata/run.json').exists() and not (run/'failure_before_portal_retry.json').exists():
                        (run/'failure.json').rename(run/'failure_before_portal_retry.json')
                    else:
                        continue
                run.mkdir(parents=True, exist_ok=True)
                reference, opened, staging = [run/p for p in ('reference','open','textured')]
                try:
                    print(name, 'ATTEMPT', attempt, 'LAYOUT', seed, flush=True)
                    config_path = run/'candidate_config.json'
                    if config_path.exists():
                        config = json.loads(config_path.read_text())
                    else:
                        config = sample_organic_config(tier, index, seed)
                        atomic_json(config_path, config)
                    if reference.exists():
                        saved = verify_bundle(reference)
                        if saved['seed'] != seed or json.loads((reference/'metadata/config.json').read_text()) != config:
                            raise ValueError('Resume configuration mismatch')
                    else:
                        print(name, 'GEOMETRY + NAVIGATION', flush=True)
                        # Native spatial-index libraries are isolated per scene;
                        # a long batch must not retain their allocator state.
                        with (run/'generation.log').open('w',encoding='utf-8') as log:
                            subprocess.run([sys.executable, '-c',
                                'import sys; from cave_composer.pipeline import generate; generate(sys.argv[1],int(sys.argv[2]),sys.argv[3],render=False)',
                                str(config_path),str(seed),str(reference)],cwd=REPO,
                                stdout=log,stderr=subprocess.STDOUT,check=True)
                    print(name, 'PORTALS', flush=True)
                    portal_attempts=[]
                    for inset in (0., .35, .7, 1.05):
                        opened=run/('open' if inset==0 else f'open_inset_{round(inset*100):03d}')
                        try:
                            if not opened.exists():
                                export_portals(reference, opened, terminal_inset=inset)
                            verify_portal_export(opened, reference)
                            portal_attempts.append({'inset_metres':inset,'status':'PASS'})
                            break
                        except ValueError as exc:
                            portal_attempts.append({'inset_metres':inset,'status':'FAIL','error':str(exc)})
                    else:
                        atomic_json(run/'portal_attempts.json',portal_attempts)
                        raise ValueError(f'No valid terminal section: {portal_attempts}')
                    atomic_json(run/'portal_attempts.json',portal_attempts)
                    verify_portal_export(opened, reference)
                    blender_run(args.blender,'cave_composer/blender_audit.py',['--scene',opened],run/'audit.log')
                    print(name, 'TEXTURES + EXPORT', flush=True)
                    if not (staging/'export_verification.json').exists():
                        blender_run(args.blender,'scripts/export_textured_cave.py',
                                    ['--scene',opened,'--output',staging,'--name',name,'--resolution',4096],run/'export.log')
                    entry = {'difficulty':tier,'index':index,'name':name,'folder':f'{tier}/scene_{index:03d}'}
                    checked = verify(run, entries=[{**entry,'folder':'textured'}])[0]
                    checked['folder'] = entry['folder']
                    routes = build_routes(config)
                    graph = navigation_graph(routes,[])
                    source_metrics = json.loads((reference/'metadata/metrics.json').read_text())
                    meta = {**entry,'seed':seed,'source':str(reference),'open':str(opened),
                            'main_route_length_m':float(routes[0]['s'][-1]),
                            'total_route_length_m':float(sum(r['s'][-1] for r in routes)),
                            'nominal_width_m':config['corridor']['width'],'nominal_height_m':config['corridor']['height'],
                            'turn_angles_deg':[],'curved_segments':sum(e['type']=='curve' for r in routes for e in r['events']),
                            'max_absolute_slope_deg':source_metrics['max_slope'],
                            'elevation_range_m':source_metrics['vertical_range'],
                            'branches':len(config['branches']),'chambers':len(config['chambers']),
                            'bottlenecks':len(config['bottlenecks']),'loops':graph['cycle_rank'],
                            'dead_ends':sum(n['semantic_type']=='dead_end' for n in graph['nodes']),
                            'topology_family':config['sampling']['family'],'layout_attempts':config['sampling']['layout_attempts'],
                            'robot_required_radius_m':config['robot']['radius']+config['robot']['margin'],
                            'path_clearance_lower_bound_m':min(f['crossing_certificate']['continuous_clearance_lower_bound'] for f in checked['formats'].values()),
                            'terminal_inset_metres':inset,
                            'difficulty_scope':'Designed geometry/morphology tiers, not measured policy performance',
                            'verification':checked,'reused_existing':False}
                    atomic_json(staging/'metadata.json',meta)
                    atomic_json(staging/'portable_verification.json',checked)
                    render_overview(staging)
                    final.parent.mkdir(parents=True,exist_ok=True)
                    safe_rename(staging,final)
                    state['assets'].append(meta)
                    atomic_json(state_path,state)
                    print(name,'PASS',len(state['assets']),'/ 15',flush=True)
                    break
                except Exception as exc:
                    error={'difficulty':tier,'index':index,'seed':seed,'attempt':attempt,
                           'error':f'{type(exc).__name__}: {exc}','diagnostics':str(run)}
                    atomic_json(run/'failure.json',error)
                    (run/'traceback.txt').write_text(traceback.format_exc(),encoding='utf-8')
                    state['failed_attempts'].append(error)
                    atomic_json(state_path,state)
                    print('REJECTED',error,flush=True)
            else:
                raise RuntimeError(f'{tier}/{index}: candidate budget exhausted; diagnostics retained')
    old_manifest=json.loads((root/'batch_manifest.json').read_text(encoding='utf-8'))
    easy=[a for a in old_manifest['assets'] if a['difficulty']=='easy']
    assert len(easy)==15
    if not (collection/'easy').exists():
        shutil.copytree(root/'easy',collection/'easy')
    assets=easy+state['assets']
    targets={'easy':15,'medium':10,'hard':5}
    archived=work/'previous_collection'
    manifest={'schema_version':1,'status':'COMPLETE','counts':targets,'targets':targets,'assets':assets,
              'collection_revision':'organic_diversity_v02','failed_attempts':state['failed_attempts'],
              'previous_collection':str(archived),
              'difficulty_scope':'Curated morphology coverage; not calibrated navigation difficulty or fitted real-cave geometry'}
    atomic_json(collection/'batch_manifest.json',manifest)
    atomic_json(collection/'verification.json',[a['verification'] for a in assets])
    write_gallery(collection,assets,targets)
    readme='''# Cave Composer — diverse cave assets

Easy 15 / medium 10 / hard 5. [Open gallery](index.html).

Easy assets are byte-for-byte unchanged. Medium and hard now use cubic meanders,
curved blind branches, asymmetric bypass loops, chambers, varying cross-sections
and elevation. Family quotas ensure mixed structural coverage; seeds randomize
each layout. Difficulty is a design label, not measured policy performance.

Each scene directory contains GLB, OBJ, MTL, 4K basecolor/normal textures, navigation,
checks and an overall route image. Move the whole directory for OBJ. GLB uses
metres/Y-up; OBJ and navigation_z_up.json use metres/Z-up.

All accepted assets pass independent path planning, dual-mesh reference checks,
two-portal export, nonadjacent triangle intersection audit and actual GLB/OBJ
reimport/texture/clearance checks. Rejected candidates remain in the manifest.
The open shell has no exterior terrain or rock thickness. Geometry is procedural;
it is not a reconstruction or statistically fitted model of a real cave.
'''
    (collection/'README.md').write_text(readme,encoding='utf-8')
    checksum_tree(collection)
    # Both moves are restricted to verified absolute paths inside this repository.
    # The full prior collection remains available; restore it if promotion fails.
    safe_rename(root,archived)
    try:
        safe_rename(collection,root)
    except Exception:
        safe_rename(archived,root)
        raise
    state.update(status='COMPLETE',published_root=str(root),previous_collection=str(archived))
    atomic_json(state_path,state)
    print('PUBLISHED',root,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',default='exports/caves_difficulty_v01')
    parser.add_argument('--work',default='outputs/difficulty_diversity_v02')
    parser.add_argument('--blender',default='D:/Blender/blender.exe')
    parser.add_argument('--attempts',type=int,default=8)
    main(parser.parse_args())
