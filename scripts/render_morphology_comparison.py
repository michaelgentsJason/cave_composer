"""Blender: matched inspection images from paired portable GLB exports."""
import argparse
import json
from pathlib import Path
import sys
import bpy
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cave_composer.blender_render import aim,light
from cave_composer.routes import build_routes


def render(root,samples=96):
    root=Path(root).resolve();records=[]
    for name in ['before','after']:
        folder=root/name;bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(folder/(name+'.glb')))
        scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=samples
        scene.cycles.use_denoising=True
        prefs=bpy.context.preferences.addons['cycles'].preferences
        try:
            prefs.compute_device_type='OPTIX';prefs.get_devices()
            for d in prefs.devices:d.use=d.type=='OPTIX'
            if any(d.use for d in prefs.devices):scene.cycles.device='GPU'
        except Exception:pass
        scene.render.resolution_x,scene.render.resolution_y=1600,1000;scene.render.resolution_percentage=100
        scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
        scene.world=bpy.data.worlds.new('Matched neutral lighting');scene.world.use_nodes=True
        scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.005
        route=build_routes(json.loads((folder/'config.json').read_text()))[0]['points']
        objects=[o for o in scene.objects if o.type=='MESH']
        materials={o.name:list(o.data.materials) for o in objects}
        clay=bpy.data.materials.new('Neutral geometry inspection');clay.use_nodes=True
        bsdf=clay.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=(.4,.43,.45,1)
        bsdf.inputs['Roughness'].default_value=.83
        lamps=[light('Key',[0,0,0],650,.5,color=(1,.96,.91)),light('Fill',[0,0,0],210,.8,color=(.9,.95,1)),light('Bounce',[0,0,0],120,.7)]
        data=bpy.data.cameras.new('Matched camera');data.lens=19;data.clip_start=.04
        camera=bpy.data.objects.new('Matched camera',data);bpy.context.collection.objects.link(camera);scene.camera=camera
        for i,fraction in enumerate([.28,.44,.65],1):
            j=round((len(route)-1)*fraction);p=route[j];target=route[min(j+18,len(route)-1)]
            tangent=(target-p)/np.linalg.norm(target-p)
            camera.location=p;aim(camera,target)
            lamps[0].location=p-tangent*.35+[0,0,.25];lamps[1].location=p+tangent*.9+[0,0,.2];lamps[2].location=target
            for mode in ['textured','clay']:
                for o in objects:
                    o.data.materials.clear()
                    for m in (materials[o.name] if mode=='textured' else [clay]):o.data.materials.append(m)
                image=f'{mode}_{i:02d}.png';scene.render.filepath=str(folder/image)
                bpy.ops.render.render(write_still=True)
                records.append({'case':name,'view':i,'mode':mode,'image':name+'/'+image,'position':p.tolist(),
                                'target':target.tolist(),'lens_mm':19,'lights':[{'position':list(l.location),'energy':l.data.energy} for l in lamps]})
        for o in objects:
            o.data.materials.clear()
            for m in materials[o.name]:o.data.materials.append(m)
        bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(folder/'inspection.blend'))
    (root/'render_views.json').write_text(json.dumps({'views':records,'samples':samples,'resolution':[1600,1000],
        'scope':'Identical world-space cameras, lighting, material and render settings across both GLBs; clay has no normal map'},indent=2),encoding='utf-8')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--samples',type=int,default=96)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);render(a.root,a.samples)
