"""Structural coverage and independent search on adversarial final geometry."""
import numpy as np
import pytest
import trimesh
from cave_composer.dataset import sample_config, scene_seed, generate_dataset
from cave_composer.routes import build_routes, navigation_graph
from cave_composer.planning import plan_navigation, certify_polyline


@pytest.mark.parametrize('family,cycles,minimum_branches,minimum_chambers', [
    ('winding', 0, 0, 0), ('branching', 0, 1, 0), ('loop', 1, 1, 0),
    ('chambers', 0, 0, 2), ('multi_loop', 2, 2, 0)])
def test_grammar_support_and_nonzero_rejoin_segments(family, cycles, minimum_branches, minimum_chambers):
    split = 'ood_topology' if family == 'multi_loop' else 'train'
    for seed in (31000, 31003):
        spec = sample_config(split, 'hard', seed, 'topology_v03', family)
        assert spec == sample_config(split, 'hard', seed, 'topology_v03', family)
        routes = build_routes(spec)
        graph = navigation_graph(routes, [])
        assert graph['cycle_rank'] == cycles
        assert len(spec['branches']) >= minimum_branches
        assert len(spec['chambers']) >= minimum_chambers
        for route in routes:
            assert np.linalg.norm(np.diff(route['points'], axis=0), axis=1).min() > 1e-8
        assert spec['sampling']['layout_attempts'] == 1 + sum(spec['sampling']['rejected_layouts'].values())


def test_realized_factors_and_held_out_topology():
    turn_counts = set()
    for split in ('train', 'ood_composition', 'ood_geometry', 'ood_topology'):
        for seed in range(4):
            spec = sample_config(split, 'hard', seed, 'topology_v03')
            commands = spec['route'] + [c for b in spec['branches'] for c in b['route']]
            actual = {'sharp': any(abs(c.get('turn', 0)) >= 60 for c in commands),
                      'narrow': spec['corridor']['width'] <= 3.6,
                      'descending': any(c.get('slope', 0) <= -10 for c in spec['route'])}
            assert actual == spec['ood_factors']
            if split in ('train', 'ood_topology'):
                assert not all(actual.values())
            else:
                assert all(actual.values())
            turn_counts.add(sum('turn' in c for c in spec['route']))
            if split == 'ood_topology':
                assert spec['sampling']['family'] == 'multi_loop'
    assert len(turn_counts) >= 3
    with pytest.raises(ValueError, match='outside the declared support'):
        sample_config('train', 'hard', 1, 'topology_v03', 'multi_loop')
    assert {scene_seed('train', i) for i in range(100)}.isdisjoint({scene_seed('ood_topology', i) for i in range(100)})


def test_layout_rejections_are_recorded_and_do_not_advance_material_rng(monkeypatch):
    from cave_composer import sampling
    base = sample_config('train', 'hard', 31000, 'topology_v03', 'winding')
    original = sampling.layout_screen
    calls = []
    def screen(spec):
        calls.append(1)
        return 'injected_layout_conflict' if len(calls) <= 2 else original(spec)
    monkeypatch.setattr(sampling, 'layout_screen', screen)
    sampled = sample_config('train', 'hard', 31000, 'topology_v03', 'winding')
    assert sampled['sampling']['rejected_layouts']['injected_layout_conflict'] == 2
    assert sampled['material'] == base['material']


def _room(obstacle_width=4.):
    outer = trimesh.creation.box(extents=[10, 10, 4]); outer.invert()
    rock = trimesh.creation.box(extents=[1, obstacle_width, 3.9])
    mesh = trimesh.util.concatenate([outer, rock])
    voxel = .25
    origin = np.array([-5., -5., -2.])
    axes = [np.arange(41), np.arange(41), np.arange(17)]
    xyz = np.stack(np.meshgrid(*axes, indexing='ij'), axis=-1) * voxel + origin
    free = np.all(np.abs(xyz) < [5, 5, 2], axis=-1)
    free &= ~np.all(np.abs(xyz) <= [0.5, obstacle_width / 2, 1.95], axis=-1)
    return mesh, free.astype(float) * 2 - 1, origin, voxel


def test_search_finds_detour_without_any_reference_route():
    mesh, grid, origin, voxel = _room()
    start, goal = [-4, 0, 0], [4, 0, 0]
    assert certify_polyline(mesh, [start, goal], .35)['status'] == 'FAIL'
    result = plan_navigation(mesh, grid, origin, voxel, start, goal, .35)
    assert result['status'] == 'PASS'
    assert result['length_metres'] > 8
    assert np.max(np.abs(np.asarray(result['points'])[:, 1])) > 2.35
    assert result['collision_certificate']['continuous_clearance_lower_bound'] > .35


def test_search_rejects_disconnection_and_exhaustion():
    mesh, grid, origin, voxel = _room(10.)
    result = plan_navigation(mesh, grid, origin, voxel, [-4, 0, 0], [4, 0, 0], .35)
    assert result['status'] == 'FAIL'
    assert result['reason'] == 'no_connection_in_conservative_grid'
    mesh, grid, origin, voxel = _room()
    result = plan_navigation(mesh, grid, origin, voxel, [-4, 0, 0], [4, 0, 0], .35, max_expansions=1)
    assert result['status'] == 'FAIL' and result['reason'] == 'search_budget_exhausted'


def test_stale_occupancy_cannot_certify_a_mesh_blocker():
    mesh, grid, origin, voxel = _room(10.)
    # Deliberately erase the blocker in the search grid, retaining it in the
    # actual final mesh. The independent final-mesh certificate must reject it.
    grid[1:-1, 1:-1, 1:-1] = 1.
    result = plan_navigation(mesh, grid, origin, voxel, [-4, 0, 0], [4, 0, 0], .35)
    assert result['status'] == 'FAIL'
    assert result['reason'] == 'candidate_failed_final_mesh_certificate'


def test_new_distribution_rejects_support_mismatch_before_output(tmp_path):
    output = tmp_path / 'bad'
    with pytest.raises(ValueError):
        generate_dataset({'sampler': 'topology_v03', 'family': 'multi_loop', 'split': 'train'}, 1, output=output)
    assert not output.exists()
