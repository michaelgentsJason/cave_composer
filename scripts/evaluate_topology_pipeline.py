"""Recorded v0.3 engineering evaluation; no PLUME or policy-performance claims."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time
import numpy as np
import yaml
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cave_composer.dataset import generate_dataset, sample_config
from cave_composer.bundle import atomic_json, verify_bundle, environment_signature


def summarize(root, manifest):
    metrics = []
    for record in manifest['records']:
        if record['status'] == 'VALID':
            verify_bundle(root / record['path'])
            metrics.append(record['metrics'])
    measures = {}
    for key in ['total_length', 'num_turns', 'branch_count', 'loop_count', 'chamber_count',
                'junction_count', 'dead_end_count', 'minimum_width', 'planned_path_clearance',
                'planning_seconds', 'generation_seconds', 'layout_attempts']:
        values = [m[key] for m in metrics if m.get(key) is not None]
        if values:
            measures[key] = {'min': float(min(values)), 'median': float(np.median(values)), 'max': float(max(values))}
    signatures = Counter(f"cycles={m['loop_count']},junctions={m['junction_count']},dead_ends={m['dead_end_count']}" for m in metrics)
    return {'requested': manifest['requested'], 'valid': manifest['valid'], 'failed': manifest['invalid'],
            'independent_path_pass': sum(m['independent_path_found'] for m in metrics),
            'measures': measures, 'coarse_structural_signatures': dict(signatures),
            'signature_scope': 'Cycle/junction/dead-end counts, not a graph-isomorphism or naturalness metric.',
            'failures': [{'index': r['index'], 'seed': r['seed'], 'status': r['status'],
                          'checks': r.get('failed_checks', []), 'error': r.get('error')} for r in manifest['records'] if r['status'] != 'VALID']}


def make_index(root, groups):
    import html
    cards = []
    for name, result in groups.items():
        folder = root / name
        image = next(folder.glob('scene_*/previews/overview.png'), None)
        if image is None:
            image = next(folder.glob('scene_*/previews/topology.png'), None)
        picture = f'<img src="{image.relative_to(root).as_posix()}" alt="{html.escape(name)}">' if image else ''
        cards.append(f'<article><a href="{name}/index.html">{picture}<h2>{html.escape(name)}</h2></a><p>{result["valid"]}/{result["requested"]} valid · {result["independent_path_pass"]} certified planned paths</p></article>')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Cave Composer v0.3 review</title><style>:root{color-scheme:dark;font-family:system-ui;background:#101b22;color:#e8f0f3}body{max-width:1400px;margin:36px auto;padding:0 20px}h1{font-size:34px}p{color:#b5c6d0;line-height:1.6}a{color:#8bd7c8}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}article{padding:16px;background:#1b2a33;border:1px solid #344a57;border-radius:10px}img{width:100%;aspect-ratio:1.6;object-fit:contain}h2{font-size:20px}</style><body><h1>Cave Composer v0.3 / structural diversity and navigation checks</h1><p>Legacy sampler and four training families, plus held-out geometry, factor combinations and two-cycle topology. Every requested seed remains recorded. This is an offline engineering evaluation, not a PLUME comparison or robot training result.</p><p><a href="evaluation.json">Raw evaluation</a> · <a href="configuration_coverage.json">Configuration coverage (no meshes)</a></p><div class="grid">''' + ''.join(cards) + '</div></body></html>'
    (root / 'index.html').write_text(page, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='outputs/pipeline_v03_final')
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--per-family', type=int, default=4)
    parser.add_argument('--base-seed', type=int, default=32000)
    parser.add_argument('--render', action='store_true')
    parser.add_argument('--blender')
    args = parser.parse_args()
    root = Path(args.output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    groups = {}
    jobs = [('legacy_v02', 'legacy_v02', 'mixed', 'train', args.per_family * 2)]
    jobs += [(family, 'topology_v03', family, 'train', args.per_family) for family in ['winding', 'branching', 'loop', 'chambers']]
    jobs += [('ood_geometry', 'topology_v03', 'mixed', 'ood_geometry', args.per_family),
             ('ood_composition', 'topology_v03', 'mixed', 'ood_composition', args.per_family),
             ('ood_topology', 'topology_v03', 'multi_loop', 'ood_topology', args.per_family)]
    for name, sampler, family, split, count in jobs:
        distribution = {'schema_version': 1, 'sampler': sampler, 'family': family,
                        'split': split, 'difficulty': 'hard', 'base_seed': args.base_seed}
        path = root / name
        manifest = generate_dataset(distribution, count, args.workers, path, render=args.render,
                                    blender=args.blender, save_blend=args.render, resume=path.exists())
        groups[name] = summarize(path, manifest)
        result = {'schema_version': 1, 'groups': groups, 'environment': environment_signature(),
                  'seconds_this_invocation': time.perf_counter() - started,
                  'rendered': args.render, 'same_geometry_resolution': True,
                  'scope': 'Different layouts and lengths: counts demonstrate coverage and operational feasibility; times and pass rates do not establish superiority over PLUME or a controlled causal benefit.'}
        atomic_json(root / 'evaluation.json', result)
        make_index(root, groups)
        print(json.dumps({'group': name, **{k: groups[name][k] for k in ['requested', 'valid', 'failed']}}), flush=True)
    coverage = {}
    for sampler in ('legacy_v02', 'topology_v03'):
        histogram = Counter()
        rejected = Counter()
        attempts = []
        for seed in range(args.base_seed + 1000, args.base_seed + 1100):
            try:
                spec = sample_config('train', 'hard', seed, sampler)
            except ValueError as exc:
                rejected[str(exc)] += 1
                continue
            turns = sum('turn' in c for c in spec['route'])
            loops = sum('rejoin_at' in b for b in spec['branches'])
            key = f"turns={turns},branches={len(spec['branches'])},cycles={loops},chambers={len(spec['chambers'])}"
            histogram[key] += 1
            attempts.append(spec.get('sampling', {}).get('layout_attempts', 1))
        coverage[sampler] = {'requested_configs': 100, 'accepted_configs': sum(histogram.values()),
                              'coarse_configuration_signatures': dict(histogram), 'unique_signatures': len(histogram),
                              'layout_attempts': attempts, 'failures': dict(rejected)}
    atomic_json(root / 'configuration_coverage.json', {'samplers': coverage,
                 'scope': 'Configuration-only screening; these 200 specifications are not meshed and are not counted as validated caves.'})
    make_index(root, groups)


if __name__ == '__main__':
    main()
