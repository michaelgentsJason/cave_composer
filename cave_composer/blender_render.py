"""Blender --background --python scripts/render_blender.py -- --scene BUNDLE.

Also accepts prototype bundles during independent modelling iteration.
"""
import argparse
import json
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector


def aim(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


def light(name,position,energy,size=2,color=(1,0.95,0.85),target=None):
    data=bpy.data.lights.new(name,'AREA' if target is not None else 'POINT')
    data.energy=energy; data.color=color
    if target is not None: data.shape='DISK'; data.size=size
    else: data.shadow_soft_size=size
    obj=bpy.data.objects.new(name,data); bpy.context.collection.objects.link(obj); obj.location=position
    if target is not None: aim(obj,target)
    return obj


def material(folder):
    settings=json.loads((folder/'materials/material.json').read_text())
    mat=bpy.data.materials.new('Dry rock — independent appearance'); mat.use_nodes=True
    n=mat.node_tree.nodes; links=mat.node_tree.links; bsdf=n.get('Principled BSDF')
    bsdf.inputs['Roughness'].default_value=settings['roughness']
    texcoord=n.new('ShaderNodeTexCoord')
    scale=n.new('ShaderNodeVectorMath'); scale.operation='SCALE'; scale.inputs[3].default_value=1/settings.get('texture_period_metres',4)
    links.new(texcoord.outputs['Object'],scale.inputs[0])
    tex=n.new('ShaderNodeTexImage'); tex.image=bpy.data.images.load(str(folder/'materials/rock_albedo.png'))
    tex.projection='BOX'; tex.projection_blend=0.22
    links.new(scale.outputs['Vector'],tex.inputs['Vector']); links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
    noise=n.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value=9; noise.inputs['Detail'].default_value=3.5; noise.inputs['Roughness'].default_value=0.72
    links.new(texcoord.outputs['Object'],noise.inputs['Vector'])
    bump=n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=0.38; bump.inputs['Distance'].default_value=0.065
    links.new(noise.outputs['Fac'],bump.inputs['Height']); links.new(bump.outputs['Normal'],bsdf.inputs['Normal'])
    return mat


def curve(points,name,color,radius=0.09):
    data=bpy.data.curves.new(name,'CURVE'); data.dimensions='3D'; data.bevel_depth=radius; data.bevel_resolution=2
    spline=data.splines.new('POLY'); spline.points.add(len(points)-1)
    for dst,p in zip(spline.points,points): dst.co=(*p,1)
    obj=bpy.data.objects.new(name,data); bpy.context.collection.objects.link(obj)
    mat=bpy.data.materials.new(name+' material'); mat.diffuse_color=(*color,1); mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(*color,1); bs.inputs['Emission Color'].default_value=(*color,1); bs.inputs['Emission Strength'].default_value=0.4
    obj.data.materials.append(mat)
    return obj


def render(folder,samples=40,width=1200,save_blend=False):
    folder=Path(folder).resolve(); previews=folder/'previews'; previews.mkdir(exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=samples
    scene.cycles.use_denoising=True
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences; prefs.compute_device_type='OPTIX'; prefs.get_devices()
        for dev in prefs.devices: dev.use=dev.type=='OPTIX'
        if any(dev.use for dev in prefs.devices): scene.cycles.device='GPU'
    except Exception: pass
    scene.render.resolution_x=width; scene.render.resolution_y=int(width*0.625); scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'; scene.render.film_transparent=False
    scene.world=bpy.data.worlds.new('Neutral world'); scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(0.075,0.085,0.10,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=0.35
    scene.view_settings.view_transform='AgX'
    source=folder/'visual/mesh.npz'
    if not source.exists(): source=folder/'mesh.npz'
    data=np.load(source); vertices=data['vertices']; faces=data['faces']
    mesh=bpy.data.meshes.new('CaveSurface'); mesh.from_pydata(vertices.tolist(),[],faces.tolist()); mesh.update()
    obj=bpy.data.objects.new('Cave visual',mesh); bpy.context.collection.objects.link(obj); obj.data.materials.append(material(folder))
    for poly in mesh.polygons: poly.use_smooth=True
    nav=folder/'navigation/centerline.json'
    if nav.exists():
        nav_data=json.loads(nav.read_text()); routes=[np.asarray(r['points']) for r in nav_data['routes']]
        name=json.loads((folder/'metadata/config.json').read_text())['name']
    else:
        info=json.loads((folder/'prototype.json').read_text()); routes=[np.asarray(info['points'])]; name=info['name']
    points=routes[0]
    camdata=bpy.data.cameras.new('Camera'); cam=bpy.data.objects.new('Camera',camdata); bpy.context.collection.objects.link(cam); scene.camera=cam
    # Robot viewpoint anticipates the first feature, rather than a random wall.
    idx=min(len(points)-8,max(6,int(len(points)*0.16)))
    cam.location=points[idx]; aim(cam,points[min(idx+12,len(points)-1)])
    camdata.type='PERSP'; camdata.lens=19; camdata.clip_start=0.05; camdata.clip_end=500
    lamps=[]
    lamps.append(light('Robot key',points[max(0,idx-2)]+[0,0,0.22],430,0.5))
    lamps.append(light('Robot fill',points[min(idx+4,len(points)-1)]+[0,0,0.5],160,0.9))
    lamps.append(light('Soft distant work light',points[min(idx+26,len(points)-1)],110,0.7))
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=0.005
    scene.render.filepath=str(previews/'inside_01.png'); bpy.ops.render.render(write_still=True)
    # A second view catches the central feature/chamber and makes geometry review easier.
    idx2=min(len(points)-10,max(6,int(len(points)*0.48)))
    offset=points[idx2]-points[idx]
    cam.location=points[idx2]; aim(cam,points[min(idx2+12,len(points)-1)])
    for lamp in lamps: lamp.location+=Vector(offset)
    scene.render.filepath=str(previews/'inside_02.png'); bpy.ops.render.render(write_still=True)
    for lamp in lamps: bpy.data.objects.remove(lamp,do_unlink=True)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=0.45
    # Remove upper faces only for the documented inspection preview. Export remains sealed.
    mid=vertices[faces].mean(axis=1)
    all_points=np.concatenate(routes)
    nearest=[]
    for start in range(0,len(mid),3000):
        d=((mid[start:start+3000,None,:]-all_points[None,:,:])**2).sum(2)
        nearest.extend(d.argmin(1))
    local_z=all_points[np.array(nearest),2]
    keep=mid[:,2]<local_z+0.45
    cut=bpy.data.meshes.new('Cutaway inspection surface'); cut.from_pydata(vertices.tolist(),[],faces[keep].tolist()); cut.update()
    obj.data=cut; obj.data.materials.append(bpy.data.materials['Dry rock — independent appearance'])
    for poly in cut.polygons: poly.use_smooth=True
    for i,r in enumerate(routes): curve(r+np.array([0,0,0.12]),f'Route {i}',(0.1,0.8,0.75) if i==0 else (0.95,0.52,0.12),0.065)
    bounds=np.array([vertices.min(0),vertices.max(0)]); center=bounds.mean(0); extent=bounds[1]-bounds[0]; size=max(extent[0],extent[1],12)
    camdata.type='ORTHO'; camdata.ortho_scale=size*1.24
    cam.location=center+np.array([0,-size*0.62,size*1.22]); aim(cam,center)
    # Fit the actual camera-plane bounds, including vertical relief, rather than
    # a world-XY extent that clipped the vertical cave's far end.
    rotation=np.asarray(cam.rotation_euler.to_matrix())
    projected=(vertices-center)@rotation
    lo,hi=projected.min(0),projected.max(0)
    aspect=scene.render.resolution_x/scene.render.resolution_y
    camdata.ortho_scale=max(hi[0]-lo[0],(hi[1]-lo[1])*aspect)*1.13
    cam.location+=Vector(rotation@np.array([(lo[0]+hi[0])/2,(lo[1]+hi[1])/2,0]))
    light('Overview key',center+[0,-size*0.2,size],size*size*90,size*0.7,target=center)
    light('Overview fill',center+[size*0.5,size*0.5,size*0.8],size*size*35,size*0.6,color=(0.78,0.86,1),target=center)
    scene.render.filepath=str(previews/'overview.png'); bpy.ops.render.render(write_still=True)
    if save_blend:
        # Save intact cave with robot camera and no cutaway route overlays for editing.
        obj.data=mesh
        for item in list(bpy.data.objects):
            if item.type=='CURVE': bpy.data.objects.remove(item,do_unlink=True)
        camdata.type='PERSP'; cam.location=points[idx]; aim(cam,points[min(idx+12,len(points)-1)])
        light('Robot preview light',points[idx]+[0,0,0.2],450,0.5)
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=str(folder/'cave.blend'))
    (previews/'render_info.json').write_text(json.dumps({'blender':bpy.app.version_string,'engine':'CYCLES','device':scene.cycles.device,'samples':samples,'width':width,'neutral_water_free':True,'overview':'roof cutaway for inspection only','name':name},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--scene',required=True); p.add_argument('--samples',type=int,default=40); p.add_argument('--width',type=int,default=1200); p.add_argument('--save-blend',action='store_true')
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]); render(a.scene,a.samples,a.width,a.save_blend)
