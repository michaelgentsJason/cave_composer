"""Seeded cubic cave layouts with mixed blind branches, bypasses and chambers.

These are morphological procedural priors, not geometry fitted to real scans.
Source-level terminal and proximity screening precedes final mesh validation.
"""
from collections import Counter
import numpy as np

from .routes import build_routes, navigation_graph
from .sampling import layout_screen
from .spec import load_spec
from .portals import terminal_planes


# (family, bypass loops, blind branches, chambers). Explicit coverage prevents
# a small delivered collection from randomly collapsing to one graph family.
PROFILES = {
    'medium': [('meander', 0, 0, 2), ('blind_forks', 0, 2, 1), ('single_bypass', 1, 1, 1),
               ('chamber_chain', 0, 1, 3), ('blind_forks', 0, 3, 0), ('single_bypass', 1, 0, 2),
               ('winding_constriction', 0, 1, 1), ('chamber_forks', 0, 2, 2),
               ('single_bypass', 1, 1, 1), ('branched_meander', 0, 3, 2)],
    'hard': [('loop_and_blind_routes', 1, 2, 2), ('double_bypass', 2, 1, 1),
             ('blind_branch_network', 0, 5, 2), ('vertical_meander', 0, 4, 3),
             ('double_bypass_forks', 2, 2, 1)]}


def curve_chain(points, initial_yaw=0., end_direction=None, dimensions=None):
    """Centrally estimated tangents converted into local cubic commands."""
    points = np.asarray(points, dtype=float)
    tangents = np.empty_like(points)
    tangents[1:-1] = (points[2:] - points[:-2]) * .5
    first_length = np.linalg.norm(points[1] - points[0])
    tangents[0] = np.array([np.cos(initial_yaw), np.sin(initial_yaw), 0]) * first_length
    tangents[-1] = points[-1] - points[-2] if end_direction is None else np.asarray(end_direction) * np.linalg.norm(points[-1]-points[-2])
    commands, yaw = [], initial_yaw
    for i in range(len(points)-1):
        controls = np.array([points[i]+tangents[i]/3, points[i+1]-tangents[i+1]/3, points[i+1]])
        rotation = np.array([[np.cos(yaw), -np.sin(yaw), 0], [np.sin(yaw), np.cos(yaw), 0], [0, 0, 1]])
        local = (controls - points[i]) @ rotation
        command = {'curve': local.tolist()}
        if dimensions:
            command.update(dimensions[i % len(dimensions)])
        commands.append(command)
        yaw = float(np.arctan2(tangents[i+1, 1], tangents[i+1, 0]))
    return commands


def _index(main, fraction):
    return int(round(fraction * (len(main['points']) - 1)))


def _basis(main, fraction):
    i = _index(main, fraction)
    point = main['points'][i]
    tangent = main['points'][i+1] - main['points'][i-1]
    yaw = float(np.arctan2(tangent[1], tangent[0]))
    return point, yaw


def _bypass(main, a, b, side, rng, width, height):
    start, yaw = _basis(main, a)
    end, end_yaw = _basis(main, b)
    normal = np.array([-np.sin(yaw), np.cos(yaw), 0]) * side
    end_normal = np.array([-np.sin(end_yaw), np.cos(end_yaw), 0]) * side
    reach = float(rng.uniform(15, 23))
    p1 = start + normal*reach
    p2 = end + end_normal*reach*float(rng.uniform(.8, 1.2))
    p1[2] += (end[2] - start[2])*.3
    p2[2] -= (end[2] - start[2])*.3
    branch_yaw = yaw + side*np.pi/2
    rotation = np.array([[np.cos(branch_yaw), -np.sin(branch_yaw), 0], [np.sin(branch_yaw), np.cos(branch_yaw), 0], [0, 0, 1]])
    controls = (np.array([p1, p2, end])-start) @ rotation
    return {'at': a, 'rejoin_at': b, 'heading': side*90,
            'route': [{'curve': controls.tolist(), 'width': width, 'height': height, 'section': 'asymmetric'}]}


def _blind(main, at, rng, width, height, hard):
    start, yaw = _basis(main, at)
    heading = float(rng.choice([-1, 1]) * rng.uniform(65, 112))
    out_yaw = yaw + np.deg2rad(heading)
    forward = np.array([np.cos(out_yaw), np.sin(out_yaw), 0])
    side = np.array([-forward[1], forward[0], 0])
    length = float(rng.uniform(11, 27) if hard else rng.uniform(8, 22))
    drift = float(rng.uniform(-.45, .45)*length)
    dz = float(rng.uniform(-3.5, 2.5) if hard else rng.uniform(-1.5, 1.5))
    points = [start, start+forward*length*.48+side*drift*.15+[0, 0, dz*.4],
              start+forward*length+side*drift+[0, 0, dz]]
    dims = [{'width': max(2.8, width*float(rng.uniform(.9, 1.08))),
             'height': max(2.8, height*float(rng.uniform(.88, 1.1))),
             'section': str(rng.choice(['irregular', 'asymmetric', 'fracture', 'tall']))} for _ in range(2)]
    return {'at': at, 'heading': heading, 'route': curve_chain(points, out_yaw, dimensions=dims)}


def sample_organic_config(tier, index, seed, max_attempts=96):
    if tier not in PROFILES or not 1 <= index <= len(PROFILES[tier]):
        raise ValueError('Unsupported organic collection tier/index')
    family, cycles, blinds, chambers = PROFILES[tier][index-1]
    rng = np.random.default_rng(np.random.SeedSequence([seed, 501]))
    hard = tier == 'hard'
    rejected = Counter()
    for attempt in range(1, max_attempts+1):
        count = int(rng.integers(5, 8) if hard else rng.integers(4, 7))
        dx = rng.uniform(10, 16, count)
        x = np.r_[14., 14.+np.cumsum(dx)]
        amplitude = float(rng.uniform(10, 22) if hard else rng.uniform(8, 18))
        phase = float(rng.uniform(-np.pi, np.pi))
        frequency = float(rng.uniform(.7, 1.7))
        y = amplitude*np.sin(np.linspace(0, frequency*2*np.pi, count+1)+phase)
        y += rng.normal(0, 3, count+1)
        y -= y[0]
        grade = 3.0 if hard else 1.7
        z = np.r_[0., np.cumsum(rng.uniform(-grade, grade, count))]
        if family == 'vertical_meander':
            z = np.r_[0., np.cumsum(rng.uniform(-4.5, -.5, count))]
        width = float(rng.uniform(3.1, 3.8) if hard else rng.uniform(4.0, 5.1))
        height = float(rng.uniform(3.2, 4.3) if hard else rng.uniform(3.6, 4.6))
        dims = [{'width': max(2.8, width*float(rng.uniform(.90, 1.25))),
                 'height': max(2.8, height*float(rng.uniform(.9, 1.25))),
                 'section': str(rng.choice(['irregular', 'asymmetric', 'flattened', 'tall', 'fracture']))}
                for _ in range(count)]
        raw = {'name': f'{tier}_organic_{index:03d}', 'split': 'difficulty_diversity_v02',
               'description': f'Organic {family}; mixed morphology, not a calibrated navigation difficulty label.',
               'corridor': {'width': width, 'height': height, 'variation': .22 if hard else .18, 'section': 'irregular'},
               'route': [{'straight':14}] + curve_chain(np.column_stack([x, y, z]), end_direction=[1,0,0], dimensions=dims)
                        + [{'straight':14, 'width':width, 'height':height, 'section':'irregular'}],
               'geology': {'amplitude':float(rng.uniform(.30,.46)), 'strata':float(rng.uniform(.10,.22)),
                            'formations':int(rng.integers(18,30) if hard else rng.integers(10,22))},
               'mesh': {'max_voxels':24000000}, 'branches':[], 'chambers':[], 'bottlenecks':[]}
        main = build_routes(load_spec(raw))[0]
        loop_ranges = [(float(rng.uniform(.22,.28)), float(rng.uniform(.57,.65)))] if cycles == 1 else [(.19,.43),(.57,.81)] if cycles else []
        for a, b in loop_ranges:
            raw['branches'].append(_bypass(main, a, b, int(rng.choice([-1,1])), rng, width, height))
        forbidden = np.array([v for pair in loop_ranges for v in pair])
        anchors = rng.permutation(np.linspace(.17,.82,16))
        selected = []
        for at in anchors:
            if any(abs(at-other)<.105 for other in selected) or (len(forbidden) and np.min(abs(forbidden-at))<.065):
                continue
            selected.append(float(at))
            if len(selected) == blinds:
                break
        if blinds and len(selected) < blinds:
            rejected['anchor_spacing'] += 1
            continue
        for at in selected[:blinds]:
            raw['branches'].append(_blind(main, at, rng, width, height, hard))
        for at in np.sort(rng.choice(np.linspace(.22,.78,12), size=chambers, replace=False)):
            raw['chambers'].append({'at':float(at), 'radii':[float(rng.uniform(3.7,5.3)),float(rng.uniform(3.4,4.7)),float(rng.uniform(2.9,4.0))],
                                    'lobes':int(rng.integers(3,7))})
        if hard or family == 'winding_constriction':
            raw['bottlenecks'] = [{'at':float(rng.uniform(.3,.7)), 'length':float(rng.uniform(3,6)), 'width':2.8, 'height':3.0}]
        spec = load_spec(raw)
        routes = build_routes(spec)
        points = np.concatenate([r['points'] for r in routes])
        origins, normals = terminal_planes(routes[0]['points'])
        if any(np.min((points-origin)@normal)<-1e-6 for origin,normal in zip(origins,normals)):
            rejected['terminal_plane_route_crossing'] += 1
            continue
        slopes = np.concatenate([np.rad2deg(np.arctan2(np.abs(np.diff(r['points'],axis=0)[:,2]),
                                           np.linalg.norm(np.diff(r['points'],axis=0)[:,:2],axis=1))) for r in routes])
        if slopes.max() > (32 if hard else 24):
            rejected['slope_limit'] += 1
            continue
        reason = layout_screen(spec)
        if reason:
            rejected[reason] += 1
            continue
        raw['material'] = {'style': ['sandstone','limestone','basalt'][(index-1)%3],
                           'seed':int(seed)+300000, 'roughness':.87}
        raw['sampling'] = {'algorithm':'organic_cubic_v02', 'family':family, 'layout_attempts':attempt,
                           'rejected_layouts':dict(rejected), 'factor_scope':'designed morphology; cubic meanders, blind branches, bypass loops, chambers and width/elevation variation'}
        return load_spec(raw)
    raise ValueError(f'Organic layout exhausted {max_attempts} candidates: {tier}/{index}/{seed}: {dict(rejected)}')
