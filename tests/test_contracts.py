from copy import deepcopy
import json
import numpy as np
import pytest
import trimesh
from cave_composer.spec import load_spec
from cave_composer.routes import build_routes,navigation_graph
from cave_composer.field import CaveField
from cave_composer.pipeline import generate,mesh_digest
from cave_composer.validation import mesh_clearance,shortcut_audit,validate
from cave_composer.dataset import sample_config,scene_seed


@pytest.mark.parametrize('angle',[30,45,60,90,120,150,180,-90])
def test_arc_has_prescribed_endpoint_and_length(angle):
    s=load_spec({'route':[{'straight':5},{'turn':angle,'radius':4},{'straight':5}]})
    r=build_routes(s)[0]; event=r['events'][1]; p=r['points'][event['end_index']]
    a=np.deg2rad(angle); sign=np.sign(angle)
    assert p==pytest.approx([5+sign*4*np.sin(a),sign*4*(1-np.cos(a)),0],abs=1e-9)
    assert event['length']==pytest.approx(4*abs(a))
    assert r['s'][-1]==pytest.approx(10+4*abs(a),abs=0.01)


def test_grade_is_metric_length_not_horizontal_length():
    s=load_spec({'route':[{'straight':10,'slope':30}]})
    r=build_routes(s)[0]
    assert r['points'][-1]==pytest.approx([10*np.cos(np.pi/6),0,5])
    assert r['s'][-1]==pytest.approx(10)


def test_loop_and_dead_end_semantics():
    s=load_spec('configs/cave_g_loop.yaml'); r=build_routes(s)
    g=navigation_graph(r,[])
    assert g['cycle_rank']==1
    assert len(g['junctions'])==2
    d=load_spec('configs/cave_d_branching.yaml'); dg=navigation_graph(build_routes(d),[])
    assert dg['cycle_rank']==0
    assert sum(n['semantic_type']=='dead_end' for n in dg['nodes'])==2


@pytest.mark.parametrize('bad',[{'route':[{'straight':float('nan')}]},{'route':[{'turn':90,'radius':0}]},
                                   {'route':[{'straight':8}],'corridor':{'width':0.4}},
                                   {'route':[{'straight':8}],'mesh':{'collision_voxel':0.8}},
                                   {'route':[{'straight':8}],'corridor':{'widht':4}}])
def test_invalid_specs_are_rejected(bad):
    with pytest.raises(ValueError): load_spec(bad)


def test_determinism_and_appearance_independence():
    s=load_spec({'route':[{'straight':9}],'geology':{'formations':2},'mesh':{'visual_voxel':0.32,'collision_voxel':0.34}})
    def build(spec,seed): return CaveField(spec,build_routes(spec),seed).mesh(.32)[0]
    a=build(s,17); b=build(s,17)
    styled=deepcopy(s); styled['material']={'style':'basalt','seed':999,'roughness':0.5}
    c=build(styled,17); d=build(s,18)
    assert mesh_digest(a)==mesh_digest(b)==mesh_digest(c)
    assert mesh_digest(a)!=mesh_digest(d)
    assert a.is_watertight and a.is_winding_consistent and a.volume<0
    assert np.all(a.contains(build_routes(s)[0]['points']))
    assert mesh_clearance(a,build_routes(s)[0]['points']).min()>s['robot']['radius']+s['robot']['margin']


def test_clearance_detects_an_inserted_blocker():
    s=load_spec({'route':[{'straight':10}],'geology':{'formations':0}})
    r=build_routes(s); field=CaveField(s,r,3); mesh,grid,origin=field.mesh(.34)
    box=trimesh.creation.box(extents=[1,8,8]); box.apply_translation([5,0,0])
    blocked=trimesh.util.concatenate([mesh,box])
    report,_=validate(s,r,navigation_graph(r,[]),field,mesh,blocked,grid,origin)
    assert report['status']=='INVALID'
    assert not report['checks']['collision_route_clearance']
    assert not report['checks']['collision_route_inside']


def test_nonlocal_shortcut_detector_rejects_open_room_hairpin():
    s=load_spec({'route':[{'straight':20},{'turn':180,'radius':3},{'straight':20}]})
    r=build_routes(s); g=navigation_graph(r,[])
    room=trimesh.creation.box(extents=[40,20,10]); room.apply_translation([10,3,0])
    audit=shortcut_audit(g,room,0.55,6)
    assert audit['status']=='FAIL' and audit['shortcuts']


def test_split_supports_and_seed_namespaces():
    sets=[]
    for split in ['train','validation','id_test','ood_geometry','ood_composition']:
        sets.append({scene_seed(split,seed) for seed in range(100)})
        for seed in range(50):
            s=sample_config(split,'hard',seed); factors=s['ood_factors']
            if split in ('train','validation','id_test'): assert not all(factors.values())
            elif split=='ood_composition': assert all(factors.values())
            else: assert s['route'][1]['turn']>=120 and s['corridor']['width']<3
    for i in range(len(sets)):
        for j in range(i): assert not sets[i]&sets[j]


@pytest.fixture
def sample_bundle(tmp_path):
    s={'name':'smoke','route':[{'straight':10}],'geology':{'amplitude':0.15,'strata':0.06,'formations':0},'mesh':{'visual_voxel':0.32,'collision_voxel':0.34}}
    output=tmp_path/'scene'; result=generate(s,4,output)
    assert result['status']=='VALID'
    return output


def test_bundle_roundtrip_and_no_overwrite(sample_bundle):
    output=sample_bundle
    visual=trimesh.load(output/'visual/cave_visual.obj',force='mesh',process=False)
    assert len(visual.faces)>100
    graph=json.loads((output/'navigation/navigation_graph.json').read_text())
    assert graph['cycle_rank']==0
    assert (output/'previews/topology.png').exists()
    with pytest.raises(FileExistsError): generate(output/'metadata/config.yaml',4,output)


def test_stonefish_rotation_and_xml_file_references(sample_bundle):
    from cave_composer.stonefish import zup_to_ned,export_stonefish
    import xml.etree.ElementTree as ET
    points=np.array([[0,0,0],[1,2,3],[-2,3,-4]])
    transformed=zup_to_ned(points,20)
    assert transformed[1]==pytest.approx([1,-2,17])
    assert np.linalg.norm(transformed[2]-transformed[1])==pytest.approx(np.linalg.norm(points[2]-points[1]))
    target=sample_bundle
    scene=export_stonefish(target);root=ET.parse(scene).getroot()
    assert root.find('static/physical/mesh').attrib['convex']=='false'
    for mesh in root.findall('.//mesh'): assert (target/mesh.attrib['filename']).exists()
    assert (target/root.find('looks/look').attrib['texture']).exists()


def test_image_roi_and_restyle_preserve_geometry(tmp_path,sample_bundle):
    from PIL import Image
    from cave_composer.materials import infer_image_prior
    from cave_composer.appearance import restyle
    image=tmp_path/'rock.png';Image.fromarray(np.full((30,30,3),[110,100,80],dtype=np.uint8)).save(image)
    prior=infer_image_prior(image,tmp_path/'prior.json',[5,5,20,20])
    assert prior['palette'][1]==pytest.approx(np.array([110,100,80])/255)
    assert prior['roughness_inferred'] is False
    with pytest.raises(ValueError): infer_image_prior(image,tmp_path/'bad.json',[20,20,20,20])
    target=restyle(sample_bundle,{'style':'basalt','seed':99},tmp_path/'styled')
    checks=json.loads((target/'metadata/appearance_experiment.json').read_text())['geometry_byte_identity']
    assert all(checks.values())
