import numpy as np
import pytest
import trimesh

from cave_composer.portals import boundary_loops, open_terminal_mesh, surface_path_certificate, terminal_planes, inset_terminal_routes


def box_case():
    mesh = trimesh.creation.box(extents=[12, 6, 6])
    mesh.invert()
    route = np.array([[-4., 0, 0], [0, 0, 0], [4., 0, 0]])
    origins, normals = terminal_planes(route)
    return mesh, route, origins, normals


def test_two_real_openings_and_clear_crossing():
    mesh, route, origins, normals = box_case()
    opened, loops = open_terminal_mesh(mesh, origins, normals, [route])
    assert mesh.is_watertight and not opened.is_watertight
    assert len(loops) == 2
    crossing = np.array([[-8., 0, 0], [8., 0, 0]])
    assert surface_path_certificate(opened, crossing, .55)['status'] == 'PASS'
    # Same crossing must hit the original sealed end caps.
    assert surface_path_certificate(mesh, crossing, .55)['status'] == 'FAIL'


def test_reject_clip_through_other_route():
    mesh, route, origins, normals = box_case()
    branch = np.array([[0., 0, 0], [-5, 1, 0]])
    with pytest.raises(ValueError, match='another intended route'):
        open_terminal_mesh(mesh, origins, normals, [route, branch])


def test_reject_additional_hole():
    mesh, route, origins, normals = box_case()
    opened, _ = open_terminal_mesh(mesh, origins, normals, [route])
    # A disconnected open triangle adds a third boundary, unrelated to portals.
    triangle = trimesh.Trimesh([[0, 8, 0], [1, 8, 0], [0, 8, 1]], [[0, 1, 2]], process=False)
    damaged = trimesh.util.concatenate([opened, triangle])
    with pytest.raises(ValueError, match='exactly entrance and exit'):
        boundary_loops(damaged, origins, normals)


def test_blocker_invalidates_crossing_even_with_open_ends():
    mesh, route, origins, normals = box_case()
    opened, _ = open_terminal_mesh(mesh, origins, normals, [route])
    blocker = trimesh.creation.box(extents=[.2, 5, 5])
    blocked = trimesh.util.concatenate([opened, blocker])
    assert surface_path_certificate(blocked, [[-8, 0, 0], [8, 0, 0]], .55)['status'] == 'FAIL'


def test_reject_open_reference():
    mesh, route, origins, normals = box_case()
    opened, _ = open_terminal_mesh(mesh, origins, normals, [route])
    with pytest.raises(ValueError, match='closed'):
        open_terminal_mesh(opened, origins, normals, [route])


def test_terminal_inset_preserves_source_and_two_openings():
    mesh, route, _, _ = box_case()
    before=route.copy()
    origins,normals,trimmed=inset_terminal_routes([route],.7)
    assert np.array_equal(route,before)
    assert np.allclose(origins[:,0],[-3.3,3.3])
    opened,loops=open_terminal_mesh(mesh,origins,normals,trimmed)
    assert len(loops)==2
    assert surface_path_certificate(opened,[[-8,0,0],[8,0,0]],.55)['status']=='PASS'
    branch=np.array([[0.,0,0],[-3.8,1,0]])
    with pytest.raises(ValueError,match='another intended route'):
        open_terminal_mesh(mesh,origins,normals,[trimmed[0],branch])


def test_terminal_inset_rejects_curved_or_invalid_stubs():
    bent=np.array([[0.,0,0],[.3,0,0],[.6,.1,0],[1,.3,0],[3,2,0]])
    with pytest.raises(ValueError,match='straight stub'):
        inset_terminal_routes([bent],.7)
    for invalid in [-1,2,float('nan')]:
        with pytest.raises(ValueError,match='inset'):
            inset_terminal_routes([bent],invalid)
