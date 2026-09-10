"""Blender: bake portable UV textures, export GLB/OBJ, and reimport for checks."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import time

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cave_composer.blender_render import aim, light, material
from cave_composer.portable_mesh import clean_glb, clean_obj
from cave_composer.bundle import verify_portal_export


def export(source, output, name, resolution=4096):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError(output)
    verify_portal_export(source)
    if Path(name).name != name or not name or any(c in name for c in '/\\:'):
        raise ValueError('Export name must be a filename stem')
    if not 256 <= resolution <= 8192:
        raise ValueError('Texture resolution must be between 256 and 8192')
    config = json.loads((source / 'metadata/source_config.json').read_text(encoding='utf-8'))
    output.mkdir(parents=True)
    textures = output / 'textures'
    textures.mkdir()
    # Attribution travels with portable derivatives, not only with the source bundle.
    if (source/'materials/ATTRIBUTION.txt').exists():
        shutil.copy2(source/'materials/ATTRIBUTION.txt',output/'ATTRIBUTION.txt')
        shutil.copy2(source/'materials/material.json',output/'material_provenance.json')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'OPTIX'
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = dev.type == 'OPTIX'
        if any(dev.use for dev in prefs.devices):
            scene.cycles.device = 'GPU'
    except Exception:
        pass
    data = np.load(source / 'visual/mesh.npz')
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(data['vertices'].tolist(), [], data['faces'].tolist())
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    for face in mesh.polygons:
        face.use_smooth = True
    procedural = material(source)
    obj.data.materials.append(procedural)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.151917, island_margin=.003, area_weight=.5)
    bpy.ops.object.mode_set(mode='OBJECT')
    print(name, 'UV ready', len(mesh.polygons), 'faces', flush=True)
    images = {}
    scene.render.bake.margin = 16
    scene.render.bake.use_pass_direct = False
    scene.render.bake.use_pass_indirect = False
    scene.render.bake.use_pass_color = True
    began = time.perf_counter()
    for channel, bake_type in [('basecolor', 'DIFFUSE'), ('normal', 'NORMAL')]:
        image = bpy.data.images.new(name + '_' + channel, width=resolution, height=resolution, alpha=False)
        image.colorspace_settings.name = 'sRGB' if channel == 'basecolor' else 'Non-Color'
        target = procedural.node_tree.nodes.new('ShaderNodeTexImage')
        target.image = image
        procedural.node_tree.nodes.active = target
        bpy.ops.object.bake(type=bake_type)
        image.filepath_raw = str(textures / (channel + '.png'))
        image.file_format = 'PNG'
        image.save()
        images[channel] = image
        print(name, 'baked', channel, flush=True)
    portable = bpy.data.materials.new(name + '_textured_rock')
    portable.use_nodes = True
    portable.use_backface_culling = False
    nodes, links = portable.node_tree.nodes, portable.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['Roughness'].default_value = config['material']['roughness']
    bsdf.inputs['Metallic'].default_value = 0
    color = nodes.new('ShaderNodeTexImage')
    color.image = images['basecolor']
    links.new(color.outputs['Color'], bsdf.inputs['Base Color'])
    normal = nodes.new('ShaderNodeTexImage')
    normal.image = images['normal']
    normalmap = nodes.new('ShaderNodeNormalMap')
    links.new(normal.outputs['Color'], normalmap.inputs['Color'])
    links.new(normalmap.outputs['Normal'], bsdf.inputs['Normal'])
    mesh.materials.clear()
    mesh.materials.append(portable)
    bpy.ops.export_scene.gltf(filepath=str(output / (name + '.glb')), export_format='GLB',
                              use_selection=True, export_yup=True, export_materials='EXPORT',
                              export_cameras=False, export_lights=False, export_animations=False)
    bpy.ops.wm.obj_export(filepath=str(output / (name + '.obj')), export_selected_objects=True,
                          forward_axis='Y', up_axis='Z', export_uv=True, export_normals=True,
                          export_materials=True, path_mode='RELATIVE', export_pbr_extensions=True)
    cleanup = {'glb': clean_glb(output / (name + '.glb')), 'obj': clean_obj(output / (name + '.obj'))}
    (output / 'precision_cleanup.json').write_text(json.dumps(cleanup, indent=2), encoding='utf-8')
    shutil.copy2(source / 'navigation/portal_path.json', output / 'navigation_z_up.json')
    path = json.loads((source / 'navigation/portal_path.json').read_text())
    def yup(p):
        return [p[0], p[2], -p[1]]
    path['points'] = [yup(p) for p in path['points']]
    path['start'], path['goal'] = yup(path['start']), yup(path['goal'])
    path['coordinate_system'] = 'glTF world: metres, Y up; source (x,y,z) maps to (x,z,-y)'
    (output / 'navigation_glb_y_up.json').write_text(json.dumps(path, indent=2), encoding='utf-8')
    shutil.copy2(source / 'metadata/portal_validation.json', output / 'portal_validation.json')
    shutil.copy2(source / 'metadata/intersection_audit.json', output / 'intersection_audit.json')
    shutil.copy2(source / 'visual/mesh.npz', output / 'reference_visual.npz')
    shutil.copy2(source / 'metadata/source_config.json', output / 'config.json')

    # Reimport the actual GLB and render it. The preview cannot accidentally
    # rely on the original procedural shader, UV map, or external source image.
    original_faces = len(mesh.polygons)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for image in list(bpy.data.images):
        bpy.data.images.remove(image)
    bpy.ops.import_scene.gltf(filepath=str(output / (name + '.glb')))
    imported = [o for o in scene.objects if o.type == 'MESH']
    if sum(len(o.data.polygons) for o in imported) != cleanup['glb']['triangles_after']:
        raise ValueError('GLB triangle count differs from open source')
    used_images = {n.image.name for o in imported for mat in o.data.materials if mat and mat.use_nodes
                   for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image is not None}
    if len(used_images) < 2 or not all(o.data.uv_layers for o in imported):
        raise ValueError('Reimported GLB lacks UVs or baked textures')
    print(name, 'reimported GLB with images', sorted(used_images), flush=True)
    nav = json.loads((source / 'navigation/centerline.json').read_text())
    points = np.asarray(nav['routes'][0]['points'])
    index = int(len(points) * .23)
    camera_data = bpy.data.cameras.new('Interior inspection')
    camera_data.lens = 19
    camera_data.clip_start = .05
    camera = bpy.data.objects.new('Interior inspection', camera_data)
    bpy.context.collection.objects.link(camera)
    camera.location = points[index]
    aim(camera, points[min(index + 14, len(points) - 1)])
    scene.camera = camera
    scene.world = bpy.data.worlds.new('Neutral inspection world')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .1
    light('Inspection key', points[max(0, index - 2)] + [0, 0, .25], 430, .6)
    light('Inspection fill', points[index + 4] + [0, 0, .4], 180, .8)
    light('Ahead', points[min(index + 24, len(points) - 1)], 120, .7)
    scene.render.resolution_x, scene.render.resolution_y = 1200, 750
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(output / 'preview_glb_interior.png')
    bpy.ops.render.render(write_still=True)
    # Validate actual OBJ + MTL texture reimport separately too.
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.wm.obj_import(filepath=str(output / (name + '.obj')), forward_axis='Y', up_axis='Z')
    imported_obj = [o for o in scene.objects if o.type == 'MESH']
    obj_images = {n.image.filepath for o in imported_obj for mat in o.data.materials if mat and mat.use_nodes
                  for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image is not None}
    if not obj_images or sum(len(o.data.polygons) for o in imported_obj) != cleanup['obj']['triangles_after']:
        raise ValueError('OBJ geometry or textures failed reimport')
    report = {'status': 'PASS', 'blender': bpy.app.version_string, 'name': name,
              'texture_resolution': resolution, 'baked_channels': ['basecolor', 'tangent_normal'],
              'roughness_factor': config['material']['roughness'], 'metallic_factor': 0, 'water_baked': False,
              'glb_embedded_textures_reimported': sorted(used_images), 'obj_texture_paths_reimported': sorted(obj_images),
              'triangle_count': original_faces, 'obj_coordinates': 'metres, right handed, Z up',
              'precision_cleanup': cleanup,
              'glb_coordinates': 'metres, right handed, Y up',
              'normal_map_convention': 'OpenGL +Y tangent-space normal',
              'seconds': time.perf_counter() - began, 'source_open_export': str(source)}
    (output / 'export_verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(name, 'EXPORT PASS', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--resolution', type=int, default=4096)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    export(args.scene, args.output, args.name, args.resolution)
