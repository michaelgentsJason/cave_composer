import numpy as np
import pytest
import trimesh
from cave_composer.planning import certify_polyline
from cave_composer.delivery_validation import verify_delivered_task

def test_open_reference_rejected_before_contains():
    m=trimesh.creation.box([10,4,4]);m.update_faces(np.arange(len(m.faces))!=0)
    assert certify_polyline(m,[[-3,0,0],[3,0,0]],.55)['reason']=='closed_reference_protocol_not_applicable'

def test_thin_wall_between_sparse_path_vertices():
    room=trimesh.creation.box([10,4,4]);wall=trimesh.creation.box([.002,4,4]);wall.apply_translation([.037,0,0])
    mesh=trimesh.util.concatenate([room,wall])
    assert certify_polyline(mesh,[[-3,0,0],[3,0,0]],.55)['status']=='FAIL'

def test_seam_import_and_post_export_visual_change(tmp_path):
    room=trimesh.creation.box([10,4,4]);files={}
    for kind in ['visual','collision']:
        files[kind]=tmp_path/(kind+'.obj')
        # Every triangle has its own vertices: same geometric boundary.
        split=trimesh.Trimesh(room.triangles.reshape(-1,3),np.arange(len(room.faces)*3).reshape(-1,3),process=False)
        split.export(files[kind])
    before=verify_delivered_task(files,[[-3,0,0],[3,0,0]],.55)
    assert before['status']=='PASS'
    scaled=room.copy();scaled.apply_scale([1,.2,1]);scaled.export(files['visual'])
    after=verify_delivered_task(files,[[-3,0,0],[3,0,0]],.55)
    assert after['status']=='FAIL'
    assert before['meshes']['visual']['file_sha256']!=after['meshes']['visual']['file_sha256']
    assert after['meshes']['collision']['certificate']['status']=='PASS'

def test_explicit_numeric_allowance():
    mesh=trimesh.creation.box([10,4,4]);r=certify_polyline(mesh,[[-3,0,0],[3,0,0]],.55)
    assert r['numerical_allowance']>=1e-6
    assert r['continuous_clearance_lower_bound'] < r['minimum_sampled_clearance']-r['sample_max_step']/2

def test_exit_requires_real_mouths_and_interior_trace():
    from cave_composer.exit_tasks import certify_exit_trace
    room=trimesh.creation.box([10,4,4]);open_mesh=room.copy()
    open_mesh.update_faces(abs(open_mesh.face_normals[:,0])<.5)
    portals=[{'name':'entrance','center':[-4,0,0],'inward':[1,0,0],'outside_point':[-7,0,0]},
             {'name':'exit','center':[4,0,0],'inward':[-1,0,0],'outside_point':[7,0,0]}]
    loops=[{'name':p['name'],'vertices':[[p['center'][0],y,z] for y,z in [(-2,-2),(2,-2),(2,2),(-2,2)]]} for p in portals]
    report={'portals':portals,'meshes':{'collision':{'boundary_loops':loops}}}
    references={k:room for k in ['visual','collision']};surfaces={k:open_mesh for k in references}
    assert certify_exit_trace([[-7,0,0],[0,0,0],[7,0,0]],references,surfaces,report)['status']=='PASS'
    outside=[[-7,8,0],[0,8,0],[7,8,0],[7,0,0]]
    assert certify_exit_trace(outside,references,surfaces,report)['status']=='FAIL'
    back_out=[[-7,0,0],[-3,0,0],[-7,0,0],[-7,8,0],[3,8,0],[3,0,0],[7,0,0]]
    assert certify_exit_trace(back_out,references,surfaces,report)['status']=='FAIL'
