"""Blender: inspect recorded routes against cropped scan triangles in model units."""
import argparse,json,sys
from pathlib import Path
import numpy as np
import bpy
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cave_composer.blender_render import aim


def run(root):
    root=Path(root).resolve();manifest=json.loads((root/'manifest.json').read_text())
    for record in manifest['assets']:
        folder=root/record['folder'];bpy.ops.wm.read_factory_settings(use_empty=True)
        d=np.load(folder/'source_crop.npz');v=d['vertices'];f=d['faces'];rgb=d['colors']
        tree=BVHTree.FromPolygons(v.tolist(),f.tolist(),all_triangles=True,epsilon=0)
        trajectory=json.loads((folder/'candidate_route.json').read_text());p=np.array(trajectory['points'])
        distance=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
        step=.1;arc=np.linspace(0,distance[-1],int(np.ceil(distance[-1]/step))+1)
        route=np.column_stack([np.interp(arc,distance,p[:,k]) for k in range(3)])
        clearance=np.array([tree.find_nearest(Vector(q))[3] for q in route]);h=float(np.max(np.diff(arc)))
        bound=float(clearance.min()-h/2)
        selection={'trimmed':False,'original_length':float(distance[-1]),'original_bound':bound}
        if bound<=0:
            # Keep the longest continuous safe portion, never join disconnected
            # pieces across a rejected interval. This is screening, not planning.
            good=clearance>.15
            edges=np.diff(np.r_[False,good,False].astype(int))
            runs=list(zip(np.flatnonzero(edges==1),np.flatnonzero(edges==-1)))
            start,end=max(runs,key=lambda x:x[1]-x[0])
            assert end-start>=10,'No useful continuous candidate remains'
            selection.update(trimmed=True,retained_arc_interval=[float(arc[start]),float(arc[end-1])],selection_threshold=.15)
            route=route[start:end];clearance=clearance[start:end];arc=arc[start:end]
            bound=float(clearance.min()-h/2)
        support=[]
        for q in route[::max(1,len(route)//80)]:
            hit=[]
            for direction in [(0,0,-1),(0,0,1),(0,1,0),(0,-1,0)]:
                hit.append(tree.ray_cast(Vector(q),Vector(direction),float(np.median(clearance)*15))[0] is not None)
            support.append(hit)
        report={'scale_status':'unverified_model_units','route_source':'reconstructed camera positions; not independent planning',
                'path_length_model_units':float(np.linalg.norm(np.diff(route,axis=0),axis=1).sum()),'minimum_sampled_distance':float(clearance.min()),
                'route_selection':selection,
                'maximum_sample_spacing':h,'surface_clearance_lower_bound':bound,
                'clearance_to_recorded_triangles_positive':bool(bound>0),
                'physical_robot_passability':'PENDING_SCALE_AND_SCAN_COMPLETENESS',
                'inside_test_performed':False,'holes_filled':False,
                'directional_surface_coverage':np.mean(support,axis=0).tolist(),
                'coverage_directions':['down','up','+Y','-Y'],'coverage_max_range':float(np.median(clearance)*15),
                'limitations':['Open scan boundaries and missing surfaces are not certified free space.',
                               'Positive distance does not establish inside/outside or metric robot clearance.']}
        (folder/'route_check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        (folder/'route.json').write_text(json.dumps({'points':route.tolist(),'units':'unscaled_model_units','source_camera_ids':trajectory['camera_ids']},indent=2),encoding='utf-8')
        del tree
        mesh=bpy.data.meshes.new('Original cropped triangles');mesh.vertices.add(len(v));mesh.vertices.foreach_set('co',v.ravel())
        mesh.loops.add(len(f)*3);mesh.loops.foreach_set('vertex_index',f.ravel());mesh.polygons.add(len(f))
        mesh.polygons.foreach_set('loop_start',np.arange(len(f),dtype=np.int32)*3);mesh.polygons.foreach_set('loop_total',np.full(len(f),3,dtype=np.int32));mesh.update()
        obj=bpy.data.objects.new('Cropped scan',mesh);bpy.context.collection.objects.link(obj);bpy.context.view_layer.objects.active=obj;obj.select_set(True)
        for poly in mesh.polygons:poly.use_smooth=True
        colors=mesh.color_attributes.new(name='SourceRGB',type='FLOAT_COLOR',domain='POINT')
        linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
        colors.data.foreach_set('color',np.column_stack([linear,np.ones(len(linear))]).astype('float32').ravel())
        mat=bpy.data.materials.new('Captured vertex appearance');mat.use_nodes=True
        nodes=mat.node_tree.nodes;nodes.clear();out=nodes.new('ShaderNodeOutputMaterial');em=nodes.new('ShaderNodeEmission');attribute=nodes.new('ShaderNodeVertexColor');attribute.layer_name='SourceRGB'
        mat.node_tree.links.new(attribute.outputs['Color'],em.inputs['Color']);mat.node_tree.links.new(em.outputs[0],out.inputs['Surface']);obj.data.materials.append(mat)
        scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
        try:
            prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
            for dev in prefs.devices:dev.use=dev.type=='OPTIX'
            if any(dev.use for dev in prefs.devices):scene.cycles.device='GPU'
        except Exception:pass
        scene.render.resolution_x,scene.render.resolution_y=1400,875;scene.render.resolution_percentage=100
        scene.view_settings.view_transform='Standard';scene.world=bpy.data.worlds.new('Black outside scan');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=0
        data=bpy.data.cameras.new('Inspection');camera=bpy.data.objects.new('Inspection',data);bpy.context.collection.objects.link(camera);scene.camera=camera;data.lens=22;data.clip_start=.01;data.clip_end=1000
        views=[]
        for i,fraction in enumerate([.27,.67],1):
            j=round((len(route)-1)*fraction);camera.location=route[j];target=route[min(j+max(10,round(len(route)*.12)),len(route)-1)];aim(camera,target)
            image=f'inside_{i:02d}.png';scene.render.filepath=str(folder/image);bpy.ops.render.render(write_still=True)
            views.append({'image':image,'position':list(camera.location),'target':target.tolist()})
        bpy.ops.wm.save_as_mainfile(filepath=str(folder/'inspection.blend'))
        (folder/'render_views.json').write_text(json.dumps({'views':views,'appearance':'original captured vertex RGB, emissive display; no generated relighting','scale_status':'unverified'},indent=2),encoding='utf-8')
        print(record['folder'],report,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',default='exports/metashape_crops_v01')
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);run(a.root)
