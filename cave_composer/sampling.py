"""Bounded, deterministic sampling of route grammars with explicit cycle support.

Layout rejection is part of the algorithm, before meshing. Its diagnostics stay
in the accepted CaveSpec; a failed scene seed is never replaced by another seed.
"""
from collections import Counter
import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from .routes import build_route, build_routes, navigation_graph
from .spec import load_spec


FAMILIES = ('winding', 'branching', 'loop', 'chambers')


def _anchor(main, command, offset):
    event = main['events'][command]
    index = int(round(event['start_index'] + offset * (event['end_index'] - event['start_index'])))
    index = int(np.clip(index, np.ceil(.05 * (len(main['points']) - 1)), np.floor(.95 * (len(main['points']) - 1))))
    return index, index / (len(main['points']) - 1)


def _loop(main, start_x, end_x, side, radius, reach):
    # Loops attach to the first, horizontal main passage. Derive lengths from
    # the actual sampled anchors so the branch rejoins without a diagonal seam.
    first = main['events'][0]
    start, at = _anchor(main, 0, start_x / first['length'])
    end, rejoin = _anchor(main, 0, end_x / first['length'])
    span = main['points'][end, 0] - main['points'][start, 0]
    return {'at': at, 'rejoin_at': rejoin, 'heading': side * 90,
            'route': [{'straight': reach}, {'turn': -side * 90, 'radius': radius},
                      {'straight': float(span - 2 * radius)},
                      {'turn': -side * 90, 'radius': radius}, {'straight': reach}]}


def layout_screen(spec):
    """Cheap screening; final meshes still require independent validation."""
    routes = build_routes(spec)
    graph = navigation_graph(routes, [])
    points = np.asarray([n['position'] for n in graph['nodes']])
    selected = np.arange(0, len(points), 5)
    samples = points[selected]
    rows, cols, values = [], [], []
    for edge in graph['edges']:
        rows.extend([edge['source'], edge['target']])
        cols.extend([edge['target'], edge['source']])
        values.extend([edge['length']] * 2)
    adjacency = csr_matrix((values, (rows, cols)), shape=(len(points), len(points)))
    distance = dijkstra(adjacency, directed=False, indices=selected)
    separation = max(spec['corridor']['width'], spec['corridor']['height']) + 2 * spec['geology']['amplitude'] + 1.0
    conflicts = 0
    for a, b in cKDTree(samples).query_pairs(separation):
        direct = np.linalg.norm(samples[a] - samples[b])
        if distance[a, selected[b]] > max(10., 2.2 * direct + 5):
            conflicts += 1
    if conflicts:
        return 'nonlocal_passage_proximity'
    # Account for actual chamber/formation bounds through the same field object.
    from .field import CaveField
    field = CaveField(spec, routes, 0)
    voxel = min(spec['mesh']['visual_voxel'], spec['mesh']['collision_voxel'])
    shape = np.ceil((field.bounds[1] - np.floor(field.bounds[0] / voxel) * voxel) / voxel).astype(int) + 1
    if np.prod(shape) > spec['mesh']['max_voxels']:
        return 'voxel_budget'
    return None


def sample_topology_config(split, difficulty, seed, family='mixed', max_attempts=32):
    if difficulty not in ('easy', 'medium', 'hard'):
        raise ValueError('difficulty must be easy, medium or hard')
    allowed = ('multi_loop',) if split == 'ood_topology' else FAMILIES
    if family != 'mixed' and family not in allowed:
        raise ValueError(f'Family {family!r} is outside the declared support for {split}: {allowed}')
    # Separate random streams keep structural layout independent of appearance.
    rng = np.random.default_rng(np.random.SeedSequence([seed, 301]))
    appearance = np.random.default_rng(np.random.SeedSequence([seed, 302]))
    selected_family = str(rng.choice(allowed)) if family == 'mixed' else family
    rejected = Counter()
    for attempt in range(1, max_attempts + 1):
        sharp, narrow, descending = map(bool, rng.integers(0, 2, 3))
        if selected_family in ('loop', 'multi_loop'):
            sharp = True  # The bypass grammar contains two 90-degree turns.
        if split == 'ood_composition':
            sharp = narrow = descending = True
        elif split == 'ood_geometry':
            sharp = narrow = descending = True
        elif sharp and narrow and descending:
            if rng.random() < .5:
                narrow = False
            else:
                descending = False
        if difficulty == 'easy' and split not in ('ood_geometry', 'ood_composition'):
            narrow = descending = False
        angle = float(rng.uniform(62, 88) if sharp else rng.uniform(25, 52))
        width = float(rng.uniform(3.0, 3.6) if narrow else rng.uniform(4.3, 5.8))
        slope = float(rng.uniform(-18, -10) if descending else rng.uniform(-4, 4))
        if split == 'ood_geometry':
            angle = float(rng.uniform(122, 155))
            width = float(rng.uniform(2.7, 2.95))
            slope = float(rng.uniform(-28, -22))
        turns = int(rng.integers(1, 3) if difficulty == 'easy' else rng.integers(2, 6))
        if selected_family == 'chambers':
            turns = max(3, turns)
        if selected_family == 'multi_loop':
            turns = min(3, turns)
        first_length = float(rng.uniform(13, 19))
        if selected_family == 'loop':
            first_length = float(rng.uniform(45, 50))
        elif selected_family == 'multi_loop':
            first_length = float(rng.uniform(82, 88))
        route = [{'straight': first_length}]
        sign = int(rng.choice([-1, 1]))
        previous_heading = 0.
        # Alternating heading targets avoid an unconstrained random walk folding
        # onto itself, while varying turn count, angles, lengths and elevation.
        for i in range(turns):
            target = sign * angle * (1. if i == 0 else float(rng.uniform(.8, 1.0))) if i % 2 == 0 else 0.
            route.append({'turn': target - previous_heading, 'radius': float(rng.uniform(5.5, 8.0))})
            command = {'straight': float(rng.uniform(13, 20)),
                       'slope': slope if i == 0 else float(rng.uniform(-6, 6)),
                       'section': str(rng.choice(['irregular', 'asymmetric', 'flattened', 'fracture', 'tall']))}
            route.append(command)
            previous_heading = target
        raw = {'name': f'{split}_{seed:06d}_{selected_family}', 'split': split,
               'description': f'{selected_family} route grammar / {difficulty}',
               'corridor': {'width': width, 'height': float(rng.uniform(3.4, 4.6)),
                            'section': str(rng.choice(['irregular', 'asymmetric', 'fracture']))},
               'route': route, 'branches': [], 'chambers': [],
               'geology': {'amplitude': float(rng.uniform(.25, .42)), 'strata': .12,
                           'formations': int(rng.integers(8, 20))},
               'ood_factors': {'sharp': sharp, 'narrow': narrow, 'descending': descending}}
        main = build_route(route, load_spec(raw)['corridor'])
        if selected_family == 'branching':
            commands = rng.choice(np.arange(0, len(route), 2), size=min(int(rng.integers(1, 4)), turns + 1), replace=False)
            for ci in sorted(commands):
                _, at = _anchor(main, int(ci), float(rng.uniform(.4, .6)))
                side = int(rng.choice([-1, 1]))
                raw['branches'].append({'at': at, 'heading': side * 90,
                                        'route': [{'straight': float(rng.uniform(12, 20))},
                                                  {'turn': side * float(rng.uniform(25, min(50, angle))), 'radius': 5.5},
                                                  {'straight': float(rng.uniform(8, 13))}]})
        elif selected_family in ('loop', 'multi_loop'):
            raw['branches'].append(_loop(main, 9., 33., -sign, 6., float(rng.uniform(10, 15))))
            if selected_family == 'multi_loop':
                raw['branches'].append(_loop(main, 49., 73., sign, 6., float(rng.uniform(10, 15))))
        elif selected_family == 'chambers':
            commands = rng.choice(np.arange(0, len(route), 2), size=int(rng.integers(2, 4)), replace=False)
            for ci in sorted(commands):
                _, at = _anchor(main, int(ci), .5)
                raw['chambers'].append({'at': at, 'radii': [float(rng.uniform(4.5, 6.0)),
                                                           float(rng.uniform(3.8, 5.5)),
                                                           float(rng.uniform(3.1, 4.4))],
                                        'lobes': int(rng.integers(3, 7))})
        # Fix appearance only after layout acceptance; its seed stream never
        # advances because of geometric candidate rejection.
        spec = load_spec(raw)
        reason = layout_screen(spec)
        if reason:
            rejected[reason] += 1
            continue
        raw['material'] = {'style': str(appearance.choice(['limestone', 'sandstone', 'basalt'])),
                           'seed': int(appearance.integers(0, 2**31)), 'roughness': .87}
        raw['sampling'] = {'algorithm': 'topology_v03', 'family': selected_family,
                           'layout_attempts': attempt, 'rejected_layouts': dict(rejected),
                           'factor_scope': 'sharp: any route turn >=60 deg; narrow: nominal corridor width <=3.6 m; descending: any main straight <=-10 deg'}
        return load_spec(raw)
    raise ValueError(f'Layout sampling exhausted {max_attempts} attempts for seed {seed}, family {selected_family}: {dict(rejected)}')
