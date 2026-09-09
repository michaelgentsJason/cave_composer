import numpy as np
import pytest
import trimesh

from cave_composer.bundle import atomic_json, bundle_checksums, verify_bundle
from cave_composer.pipeline import generate
from cave_composer.planning import NavigationSpace
from cave_composer.reference_data import audit_reference_registry, cross_section_statistics, depth_observation_statistics
from cave_composer.routes import build_routes
from cave_composer.sensors import project_body_points, stereo_rgb_rig
from cave_composer.spec import load_spec
from cave_composer.tasks import build_task_pack, load_task_pack, sample_requests


def test_cached_space_owns_occupancy_and_finds_a_real_detour():
    outer = trimesh.creation.box([10, 10, 4]); outer.invert()
    obstacle = trimesh.creation.box([1, 4, 3.9])
    mesh = trimesh.util.concatenate([outer, obstacle])
    xyz = np.stack(np.meshgrid(np.arange(41), np.arange(41), np.arange(17), indexing='ij'), axis=-1)*.25+[-5, -5, -2]
    grid = np.all(np.abs(xyz) < [5, 5, 2], axis=-1) & ~np.all(np.abs(xyz) <= [.5, 2, 1.95], axis=-1)
    space = NavigationSpace(grid, [-5, -5, -2], .25, .35)
    grid[:] = False
    result = space.plan(mesh, [-4, 0, 0], [4, 0, 0])
    assert result['status'] == 'PASS'
    assert np.max(np.abs(np.asarray(result['points'])[:, 1])) > 2.35
    assert result['length_metres'] > 8
    reverse = space.plan(mesh, [4, 0, 0], [-4, 0, 0])
    assert reverse['status'] == 'PASS'
    with pytest.raises(ValueError):
        space.plan(mesh, [np.nan, 0, 0], [0, 0, 0])


def test_task_sampler_reaches_branch_interiors_and_is_reproducible():
    spec = load_spec('configs/cave_d_branching.yaml')
    routes = build_routes(spec)
    a = sample_requests(routes, spec['branches'], 16, 17)
    assert a == sample_requests(routes, spec['branches'], 16, 17)
    assert a != sample_requests(routes, spec['branches'], 16, 18)
    assert {r['requested_class'] for r in a} == {'main_to_main', 'main_to_branch', 'branch_to_main', 'branch_to_branch'}
    for r in a:
        assert not r.get('request_error')
        if r['requested_class'] == 'branch_to_branch':
            assert r['start_route'] != r['goal_route'] and r['goal_route'] != 'main'


@pytest.fixture(scope='module')
def small_source(tmp_path_factory):
    folder = tmp_path_factory.mktemp('task-source')/'scene'
    generate({'route': [{'straight': 12}], 'geology': {'formations': 0},
              'mesh': {'visual_voxel': .3, 'collision_voxel': .34}}, seed=51, output=folder)
    return folder


def test_task_pack_preserves_source_and_portable_reset_contract(small_source, tmp_path):
    before = bundle_checksums(small_source)
    pack = tmp_path/'pack'
    result = build_task_pack(small_source, pack, count=2, seed=71)
    assert result['passed'] == 2
    contract, episodes = load_task_pack(pack)
    assert contract['policy_inputs']['sensors'] == ['rgb_left', 'rgb_right']
    assert 'planned_path' not in str(episodes) and 'occupancy' not in str(episodes)
    assert before == bundle_checksums(small_source)
    verify_bundle(small_source)
    # Rehashing a changed reset must not make it match the original certificate.
    episodes[0]['goal']['position_m'][1] += .3
    atomic_json(pack/'episodes.json', {'schema_version': 1, 'episodes': episodes})
    atomic_json(pack/'metadata/checksums.json', bundle_checksums(pack))
    with pytest.raises(ValueError, match='Episode differs'):
        load_task_pack(pack)


def test_failed_task_budget_retains_every_request(small_source, tmp_path):
    pack = tmp_path/'failed'
    result = build_task_pack(small_source, pack, count=3, seed=72, max_expansions=1)
    assert result['status'] == 'PARTIAL' and result['failed'] == 3
    assert len(list((pack/'tasks').glob('*.json'))) == 3
    assert load_task_pack(pack)[1] == []
    assert all(r['reason'] == 'search_budget_exhausted' for r in result['all_requests'])


def test_visual_rejection_cannot_be_exported_as_valid_episode(small_source, tmp_path, monkeypatch):
    monkeypatch.setattr('cave_composer.tasks.certify_polyline', lambda *a, **k: {'status': 'FAIL'})
    result = build_task_pack(small_source, tmp_path/'visual-fail', count=2, seed=71)
    assert result['passed'] == 0
    assert all(r['reason'] == 'candidate_failed_visual_mesh_certificate' for r in result['all_requests'])


def test_stereo_calibration_has_correct_sign_and_metric_disparity():
    rig = stereo_rgb_rig()
    p = np.array([[3, .2, .1], [8, -.4, -.3]])
    left, depth = project_body_points(rig, p, 'left')
    right, _ = project_body_points(rig, p, 'right')
    assert left[:, 1] == pytest.approx(right[:, 1])
    assert left[:, 0]-right[:, 0] == pytest.approx(rig['cameras']['left']['K'][0][0]*.12/depth)
    for camera in rig['cameras'].values():
        rotation = np.array(camera['T_body_from_optical'])[:3, :3]
        assert rotation.T @ rotation == pytest.approx(np.eye(3))
        assert np.linalg.det(rotation) == pytest.approx(1)


def test_reference_group_and_hash_leakage_are_rejected():
    prior = {'id': 'a', 'role': 'prior', 'source_group': 'cave_A', 'group_confirmed': True,
             'used_for_development': True, 'content_sha256': ['a'*64]}
    test = {'id': 'b', 'role': 'test', 'source_group': 'cave_A', 'group_confirmed': True,
            'used_for_development': False, 'content_sha256': ['b'*64]}
    assert audit_reference_registry({'assets': [prior, test]})['status'] == 'FAIL'
    test['source_group'] = 'cave_B'
    assert audit_reference_registry({'assets': [prior, test]})['untouched_test_ready']
    test['content_sha256'] = ['a'*64]
    assert audit_reference_registry({'assets': [prior, test]})['status'] == 'FAIL'
    test['content_sha256'] = ['b'*64]; test['group_confirmed'] = False
    assert audit_reference_registry({'assets': [test]})['status'] == 'FAIL'
    result = audit_reference_registry({'assets': [prior]})
    assert result['status'] == 'PASS' and not result['untouched_test_ready']


def test_reference_depth_uses_optical_z_and_keeps_invalid_fraction():
    d = np.full((12, 16), 2.)
    d[0, :4] = [0, np.nan, np.inf, -1]
    result = depth_observation_statistics(d, [[10, 0, 8], [0, 10, 6], [0, 0, 1]])
    assert result['optical_depth_m']['p50'] == 2
    assert result['range_m']['p50'] > 2
    assert result['valid_fraction'] == pytest.approx(188/192)
    empty = depth_observation_statistics(np.zeros((12, 16)), np.eye(3))
    assert empty['optical_depth_m'] is None


def test_cross_section_probe_recovers_known_metric_dimensions():
    room = trimesh.creation.box([12, 6, 4]); room.invert()
    points = np.column_stack([np.linspace(-4, 4, 9), np.zeros(9), np.zeros(9)])
    profile = cross_section_statistics(room, points)
    assert profile['samples_complete_inside'] == 7
    assert profile['width_m']['p50'] == pytest.approx(6)
    assert profile['height_m']['p50'] == pytest.approx(4)
    assert profile['width_height_ratio']['p50'] == pytest.approx(1.5)
    separated = cross_section_statistics(room, points, [[0, 0, 0]], junction_radius=1.1)
    assert separated['samples_complete_inside'] == 7
    assert separated['nonjunction_profile']['samples'] == 4
    assert separated['nonjunction_profile']['transverse_span_m']['p50'] == pytest.approx(6)
