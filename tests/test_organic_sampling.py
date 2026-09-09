import numpy as np
import pytest

from cave_composer.organic_sampling import sample_organic_config, PROFILES
from cave_composer.routes import build_route, build_routes, navigation_graph
from cave_composer.spec import load_spec


def test_cubic_route_world_frame_endpoint_and_spacing():
    spec = load_spec({'route': [{'curve': [[4, 0, 0], [8, 6, 2], [12, 6, 2]]}, {'straight': 3}]})
    route = build_route(spec['route'], spec['corridor'], origin=(5, 7, 2), heading=np.pi/2)
    curve_end = route['events'][0]['end_index']
    assert np.allclose(route['points'][curve_end], [-1, 19, 4])
    assert np.allclose(route['points'][-1], [-1, 22, 4])
    steps = np.linalg.norm(np.diff(route['points'], axis=0), axis=1)
    assert steps.min() > 0 and steps.max() <= .300001
    assert len(route['widths']) == len(route['heights']) == len(route['sections']) == len(route['points'])


@pytest.mark.parametrize('command', [
    {'curve': [[0, 0, 0], [3, 2, 1], [5, 2, 1]]},
    {'curve': [[1, 0, 0], [3, 2, 1], [3, 2, 1]]},
    {'curve': [[1, 0, 0], [3, 2, float('nan')], [5, 2, 1]]},
    {'curve': [[1, 0, 0], [3, 2, 1], [5, 2, 1]], 'straight': 5},
    {'curve': [[1, 0, 0], [3, 2, 1], [5, 2, 1]], 'slope': 5},
])
def test_invalid_cubic_commands_rejected(command):
    with pytest.raises(ValueError):
        load_spec({'route': [command]})


@pytest.mark.parametrize('tier,index', [('medium', 2), ('medium', 3), ('hard', 2), ('hard', 3)])
def test_organic_graph_coverage_and_reproducibility(tier, index):
    seed = (1070000 if tier == 'medium' else 1080000) + index*100
    spec = sample_organic_config(tier, index, seed)
    assert spec == sample_organic_config(tier, index, seed)
    routes = build_routes(spec)
    graph = navigation_graph(routes, [])
    _, loops, blinds, chambers = PROFILES[tier][index-1]
    assert graph['cycle_rank'] == loops
    assert sum(n['semantic_type']=='dead_end' for n in graph['nodes']) == blinds
    assert len(spec['chambers']) == chambers
    for route in routes:
        assert 0 < np.linalg.norm(np.diff(route['points'], axis=0), axis=1).min()
        assert np.linalg.norm(np.diff(route['points'], axis=0), axis=1).max() <= .300001
        if route['join_end'] is not None:
            assert np.allclose(route['points'][-1], routes[0]['points'][route['join_end']])
