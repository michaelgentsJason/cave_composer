"""Documented Stonefish 1.6 scene adapter; simulator execution is a separate stage."""
from pathlib import Path
import json
import math
import xml.etree.ElementTree as ET
import numpy as np


def zup_to_ned(points,depth=20):
    """Rotate pi about X (det=+1), then translate downward. No reflection of winding."""
    points=np.asarray(points,dtype=float)
    return points*np.array([1,-1,-1])+np.array([0,0,depth])


def export_stonefish(bundle,depth=20,jerlov=0.2):
    bundle=Path(bundle).resolve(); out=bundle/'stonefish'; out.mkdir(exist_ok=True)
    if not math.isfinite(depth) or not 0<=jerlov<=1: raise ValueError('Invalid depth / Jerlov setting')
    config=json.loads((bundle/'metadata/config.json').read_text())
    vertices=np.load(bundle/'visual/mesh.npz')['vertices']
    if zup_to_ned(vertices,depth)[:,2].min()<=0: raise ValueError('Cave intersects sea surface; increase depth')
    root=ET.Element('scenario')
    root.append(ET.Comment('Candidate scene for Stonefish 1.6. Set SimulationApp data directory to the cave bundle root. Runtime NOT validated.'))
    env=ET.SubElement(root,'environment'); ET.SubElement(env,'ned',latitude='0',longitude='0')
    ocean=ET.SubElement(env,'ocean'); ET.SubElement(ocean,'water',density='1025',jerlov=str(jerlov),temperature='15'); ET.SubElement(ocean,'waves',height='0'); ET.SubElement(ocean,'particles',enabled='false')
    atmosphere=ET.SubElement(env,'atmosphere'); ET.SubElement(atmosphere,'sun',azimuth='0',elevation='45')
    materials=ET.SubElement(root,'materials'); ET.SubElement(materials,'material',name='ComposerRock',density='2600',restitution='0.1')
    looks=ET.SubElement(root,'looks'); ET.SubElement(looks,'look',name='ComposerDryRock',rgb='1 1 1',roughness=str(config['material']['roughness']),metalness='0',texture='materials/rock_albedo.png')
    cave=ET.SubElement(root,'static',name=config['name'],type='model')
    for kind,filename in [('physical','collision/cave_collision.obj'),('visual','visual/cave_visual.obj')]:
        element=ET.SubElement(cave,kind)
        attrs={'filename':filename,'scale':'1'}
        if kind=='physical': attrs['convex']='false'
        ET.SubElement(element,'mesh',**attrs); ET.SubElement(element,'origin',xyz='0 0 0',rpy='0 0 0')
    ET.SubElement(cave,'material',name='ComposerRock'); ET.SubElement(cave,'look',name='ComposerDryRock')
    ET.SubElement(cave,'world_transform',xyz=f'0 0 {depth:g}',rpy=f'{math.pi:.15g} 0 0')
    ET.indent(root,space='  '); ET.ElementTree(root).write(out/'cave.scn',encoding='utf-8',xml_declaration=True)
    spawn=json.loads((bundle/'navigation/spawn_points.json').read_text())[0]
    goal=json.loads((bundle/'navigation/goals.json').read_text())[0]
    metadata={'status':'PARTIAL','runtime_tested':False,'target_documentation':'Stonefish 1.6',
              'data_directory':'bundle root','local_zup_to_world_ned':[[1,0,0,0],[0,-1,0,0],[0,0,-1,depth],[0,0,0,1]],
              'spawn_ned':zup_to_ned(spawn['position'],depth).tolist(),'goal_ned':zup_to_ned(goal['position'],depth).tolist(),
              'spawn_forward_ned':(np.array(spawn['forward'])*[1,-1,-1]).tolist(),
              'remaining':['Load with actual Stonefish parser','Verify concave inward boundary collision with robot and ray sensors','Measure camera and collision performance','Attach robot/camera/lights; no robot is included'],
              'notes':['MTL ignored by Stonefish; explicit look references PNG','convex=false is essential: a convex hull would fill the cave void','Blender-only bump detail is not exported to Stonefish','NED transform is a rotation, preserving winding and metric distances']}
    (out/'adapter.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    return out/'cave.scn'
