"""Blender: render three inspection views from the actual exported GLB."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cave_composer.blender_render import aim,light
from cave_composer.routes import build_routes


def render(folder,samples=96):
    folder=Path(folder).resolve();paths=list(folder.glob('*.glb'))
    if len(paths)!=1:raise ValueError('Expected one GLB')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(paths[0]))
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=samples
    scene.cycles.use_denoising=True
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
        for d in prefs.devices:d.use=d.type=='OPTIX'
        if any(d.use for d in prefs.devices):scene.cycles.device='GPU'
    except Exception:pass
    scene.render.resolution_x,scene.render.resolution_y=1800,1125
    scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
    scene.view_settings.view_transform='AgX'
    scene.world=bpy.data.worlds.new('Inspection environment');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.6,.65,.7,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.005
    spec=json.loads((folder/'config.json').read_text())
    route=build_routes(spec)[0]['points']
    key=light('Inspection key',[0,0,0],650,.5,color=(1,.96,.91))
    fill=light('Inspection fill',[0,0,0],210,.8,color=(.9,.95,1))
    forward=light('Forward bounce',[0,0,0],100,.7,color=(1,1,1))
    records=[]
    for i,fraction in enumerate([.16,.47,.74],1):
        index=round((len(route)-1)*fraction);p=route[index];target=route[min(index+20,len(route)-1)]
        tangent=(target-p)/np.linalg.norm(target-p)
        data=bpy.data.cameras.new(f'View {i}');data.lens=19;data.clip_start=.04
        cam=bpy.data.objects.new(f'View {i}',data);bpy.context.collection.objects.link(cam)
        cam.location=p;aim(cam,target);scene.camera=cam
        scene.timeline_markers.new(f'View {i}',frame=i).camera=cam;scene.frame_set(i)
        key.location=p-tangent*.35+[0,0,.25];fill.location=p+tangent*.9+[0,0,.2];forward.location=target
        for lamp in [key,fill,forward]:lamp.keyframe_insert('location',frame=i)
        bpy.context.view_layer.update()
        image=f'inside_{i:02d}.png';scene.render.filepath=str(folder/image)
        bpy.ops.render.render(write_still=True)
        records.append({'id':i,'image':image,'position':p.tolist(),'target':target.tolist(),
                        'matrix_world':[list(row) for row in cam.matrix_world]})
    scene.frame_start,scene.frame_end=1,3;scene.frame_set(1)
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(folder/'cave_easy_reference.blend'))
    (folder/'render_views.json').write_text(json.dumps({'source_glb':paths[0].name,'engine':'Cycles',
        'samples':samples,'resolution':[1800,1125],'views':records,'water_medium':False,
        'appearance':'Exported embedded basecolor and normal images; neutral inspection lighting'},indent=2),encoding='utf-8')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',required=True);p.add_argument('--samples',type=int,default=96)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);render(args.folder,args.samples)
