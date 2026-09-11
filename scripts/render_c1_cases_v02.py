"""Blender actual-mesh views: fixed pilot cases, uniform cameras, clay/textured."""
from pathlib import Path
import sys,json,hashlib
import bpy,numpy as np
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from cave_composer.blender_render import material,aim,light
OUT=ROOT/'outputs/c1_pilot_v02/renders'
OUT.mkdir(exist_ok=True)
records=[]
# Fit the union of all preregistered representative meshes once. Every overview
# uses identical scale, target and orientation, with a recorded 12% frame margin.
cloud=np.concatenate([np.load(ROOT/'outputs/c1_pilot_v02/scenes'/b/'full/visual/mesh.npz')['vertices']
                      for b in ['request_00','request_01','request_02']])
offset=np.array([15.,-31.,30.]);forward=-offset/np.linalg.norm(offset)
right=np.cross(forward,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,forward)
basis=np.column_stack([right,up,forward]);projected=cloud@basis
lo=projected.min(0);hi=projected.max(0);overview_target=((lo+hi)/2)@basis.T
overview_scale=1.12*max(hi[0]-lo[0],(hi[1]-lo[1])*1440/800)
for base in ['request_00','request_01','request_02']:
    source=ROOT/'outputs/c1_pilot_v02/scenes'/base/'full'
    for view in ['overview','interior']:
        bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene
        scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
        try:
            prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
            for dev in prefs.devices:dev.use=dev.type=='OPTIX'
            if any(dev.use for dev in prefs.devices):scene.cycles.device='GPU'
        except Exception:pass
        scene.render.resolution_x=1440;scene.render.resolution_y=800;scene.render.resolution_percentage=100
        scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
        scene.world=bpy.data.worlds.new('World');scene.world.use_nodes=True
        scene.world.node_tree.nodes['Background'].inputs[0].default_value=(1,1,1,1)
        scene.world.node_tree.nodes['Background'].inputs[1].default_value=.7 if view=='overview' else .005
        nav=json.loads((source/'navigation/centerline.json').read_text())['routes'];route=np.array(nav[0]['points'])
        meshdata=np.load(source/'visual/mesh.npz');vertices=meshdata['vertices'];faces=meshdata['faces']
        if view=='overview':
            # Inspection-only roof removal. Exported source mesh remains untouched.
            centroids=vertices[faces].mean(1)
            all_route=np.concatenate([np.array(r['points']) for r in nav])
            z=np.array([all_route[np.argmin(np.linalg.norm(all_route[:,:2]-c[:2],axis=1)),2] for c in centroids])
            faces=faces[centroids[:,2]<z+.35]
        mesh=bpy.data.meshes.new('Actual delivered geometry');mesh.from_pydata(vertices.tolist(),[],faces.tolist());mesh.update()
        obj=bpy.data.objects.new(base,mesh);bpy.context.collection.objects.link(obj)
        # Flat normals in BOTH modes make actual triangle geometry visible.
        for polygon in mesh.polygons:polygon.use_smooth=False
        textured=material(source);clay=bpy.data.materials.new('Clay without bump');clay.use_nodes=True
        shader=clay.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=(.46,.48,.49,1);shader.inputs['Roughness'].default_value=.85
        camera_data=bpy.data.cameras.new('Fixed convention');camera=bpy.data.objects.new('Camera',camera_data);bpy.context.collection.objects.link(camera);scene.camera=camera
        if view=='overview':
            target=overview_target;pos=target+offset;camera_data.type='ORTHO';camera_data.ortho_scale=overview_scale
            light('Key',[5,-5,20],1800,8);light('Fill',[20,15,12],1000,7)
            scene.render.film_transparent=True
        else:
            j=round((len(route)-1)*.28);pos=route[j];target=route[min(j+18,len(route)-1)];camera_data.lens=19
            direction=(target-pos)/np.linalg.norm(target-pos)
            light('Key',pos-direction*.3+[0,0,.25],650,.5);light('Fill',pos+direction*.9+[0,0,.2],210,.8)
            scene.render.film_transparent=False
        camera.location=pos;camera_data.clip_start=.04;aim(camera,target)
        for mode,mat in [('clay',clay),('textured',textured)]:
            obj.data.materials.clear();obj.data.materials.append(mat)
            filename=f'{base}_{view}_{mode}.png';scene.render.filepath=str(OUT/filename);bpy.ops.render.render(write_still=True)
            records.append({'base_id':base,'view':view,'mode':mode,'image':filename,'camera_position':pos.tolist(),'camera_target':target.tolist(),
                'lens_mm':camera_data.lens,'ortho_scale':camera_data.ortho_scale if view=='overview' else None,
                'inspection_cutaway':view=='overview','source_mesh_sha256':hashlib.sha256((source/'visual/mesh.npz').read_bytes()).hexdigest(),
                'normal_shading':'flat in both modes','material_source':str(source/'materials/material.json')})
        (OUT/'provenance.json').write_text(json.dumps({'blender':bpy.app.version_string,'samples':32,'resolution':[1440,800],
            'framing':'One shared projected bounding box of all three source meshes, 12 percent margin',
            'command':'blender --background --python scripts/render_c1_cases_v02.py','script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'views':records},indent=2))
