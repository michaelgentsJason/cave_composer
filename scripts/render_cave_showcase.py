"""Blender: render registered viewpoints of a cave with validated assets."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cave_composer.blender_render import aim, light, material


def render(folder, samples=80, only=None):
    folder = Path(folder).resolve()
    report = json.loads((folder / 'validation.json').read_text())
    if report['status'] != 'PASS':
        raise ValueError('Validate the asset scene first')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 8
    prefs = bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type = 'OPTIX'
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = dev.type == 'OPTIX'
        if any(dev.use for dev in prefs.devices):
            scene.cycles.device = 'GPU'
    except Exception:
        pass
    scene.render.resolution_x, scene.render.resolution_y = 1800, 1125
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    scene.world = bpy.data.worlds.new('Neutral inspection exterior')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.52, .65, .78, 1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .45
    rock = material(folder / 'scene')
    rock.name = 'Original limestone / procedural albedo and bump'
    # Supplemental small-scale grain and roughness only; no geometric displacement.
    nodes, links = rock.node_tree.nodes, rock.node_tree.links
    bsdf = nodes['Principled BSDF']
    coords = next(n for n in nodes if n.bl_idname == 'ShaderNodeTexCoord')
    previous_normal = bsdf.inputs['Normal'].links[0].from_socket
    grain = nodes.new('ShaderNodeTexNoise')
    grain.inputs['Scale'].default_value = 65
    grain.inputs['Detail'].default_value = 2
    links.new(coords.outputs['Object'], grain.inputs['Vector'])
    fine = nodes.new('ShaderNodeBump')
    fine.inputs['Strength'].default_value = .23
    fine.inputs['Distance'].default_value = .012
    links.new(grain.outputs['Fac'], fine.inputs['Height'])
    links.new(previous_normal, fine.inputs['Normal'])
    links.new(fine.outputs['Normal'], bsdf.inputs['Normal'])
    rough = nodes.new('ShaderNodeMapRange')
    rough.inputs['To Min'].default_value = .62
    rough.inputs['To Max'].default_value = .94
    links.new(grain.outputs['Fac'], rough.inputs['Value'])
    links.new(rough.outputs['Result'], bsdf.inputs['Roughness'])
    metal = bpy.data.materials.new('Dark anodized frame')
    metal.use_nodes = True
    bs = metal.node_tree.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = (.055, .065, .073, 1)
    bs.inputs['Metallic'].default_value = .65
    bs.inputs['Roughness'].default_value = .38
    checker = bpy.data.materials.new('Printed metric checkerboard')
    checker.use_nodes = True
    tex = checker.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(str(folder / 'assets/checkerboard.png'))
    tex.extension = 'EXTEND'
    checker.node_tree.links.new(tex.outputs['Color'], checker.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    checker.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .82

    def object_from_npz(path, name, mat=None):
        d = np.load(path)
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(d['vertices'].tolist(), [], d['faces'].tolist())
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        if mat:
            mesh.materials.append(mat)
        return obj

    cave = object_from_npz(folder / 'scene/visual/mesh.npz', 'Intact cave with two open portals', rock)
    for p in cave.data.polygons:
        p.use_smooth = True
    collision = object_from_npz(folder / 'scene/collision/mesh.npz', 'Collision cave (hidden)')
    collision.hide_render = collision.hide_viewport = True
    collision.display_type = 'WIRE'
    assets = json.loads((folder / 'assets/manifest.json').read_text())['assets']
    for item in assets:
        obj = object_from_npz(folder / 'assets' / item['mesh'], item['name'], rock if item['kind'] == 'rock' else metal)
        if item['kind'] == 'rock':
            for p in obj.data.polygons:
                p.use_smooth = True
        else:
            # Assign print to the existing front triangles: no coplanar overlay
            # and no discrepancy between rendered and validated collision faces.
            center = np.array(item['board_center'])
            rotation = np.array(item['rotation'])
            mesh = obj.data
            mesh.uv_layers.new()
            mesh.materials.append(checker)
            local = (np.array([v.co[:] for v in mesh.vertices]) - center) @ rotation
            for poly in mesh.polygons:
                if np.all(np.abs(local[list(poly.vertices), 1] - .025) < 2e-5):
                    poly.material_index = 1
                    for loop_id in poly.loop_indices:
                        coord = local[mesh.loops[loop_id].vertex_index]
                        mesh.uv_layers.active.data[loop_id].uv = (.5-coord[0]/.74, coord[2]/.70+.5)

    # Only a moving inspection light rig; no invented visible ceiling lights.
    key = light('Camera work light', [0, 0, 0], 360, .28, color=(1., .94, .84))
    fill = light('Camera broad fill', [0, 0, 0], 95, .8, color=(.83, .9, 1))
    distant = light('Forward inspection bounce', [0, 0, 0], 100, .65, color=(1., .95, .89))
    portal = json.loads((folder / 'scene/metadata/portal_validation.json').read_text())
    for p in portal['portals']:
        center, normal = np.array(p['center']), np.array(p['inward'])
        light(p['name'] + ' exterior', center - normal*5 + [0, 0, 2], 1800, 5,
              color=(.72, .83, 1.), target=center)
    views = json.loads((folder / 'views/cameras.json').read_text())['views']
    for view in views:
        name = f"{view['id']:02d} / {view['title']}"
        data = bpy.data.cameras.new(name)
        data.lens, data.sensor_width = view['lens_mm'], view['sensor_width_mm']
        data.clip_start, data.clip_end = .04, 1000
        cam = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(cam)
        position, target = np.array(view['position']), np.array(view['target'])
        cam.location = position
        aim(cam, target)
        frame = view['id']
        scene.timeline_markers.new(name, frame=frame).camera = cam
        scene.frame_set(frame)
        scene.camera = cam
        tangent = target-position
        tangent /= np.linalg.norm(tangent)
        key.location = position - tangent * .35 + [0, 0, .23]
        fill.location = position + tangent * .8 + [0, 0, .12]
        distant.location = target
        for lamp in [key, fill, distant]:
            lamp.keyframe_insert('location', frame=frame)
        view['matrix_world'] = [list(row) for row in cam.matrix_world]
        if only is None or frame in only:
            scene.render.filepath = str(folder / view['image'])
            bpy.ops.render.render(write_still=True)
    # Camera matrices must be evaluated after dependency graph updates.
    for view in views:
        scene.frame_set(view['id'])
        bpy.context.view_layer.update()
        view['matrix_world'] = [list(row) for row in scene.camera.matrix_world]
    (folder / 'views/render_metadata.json').write_text(json.dumps(dict(
        engine='Cycles', blender=bpy.app.version_string, device=scene.cycles.device,
        samples=samples, resolution=[1800, 1125], views=views,
        appearance='Original procedural limestone texture + procedural bump; neutral inspection lighting; no participating water medium.',
        geometry='Original generated cave, terminal caps opened; explicit rock and board assets, intact ceiling.'), indent=2), encoding='utf-8')
    scene.frame_start, scene.frame_end = 1, 8
    scene.frame_set(1)
    cave.select_set(True)
    bpy.context.view_layer.objects.active = cave
    info = bpy.data.texts.new('READ ME - registered cave showcase')
    info.write('Cave Composer: eight real camera views of the same scene.\n'
               'Timeline frames 1-8 switch cameras and work lights. Numpad 0: camera view.\n'
               'Shift+`: walk navigation. Assets are separate named objects.\n'
               'Procedural limestone, explicit floor stones, three checkerboard props.\n'
               'Geometry in meters, Z up. Open entrance and exit, intact roof.\n'
               'Not a SLAM reconstruction, sensor recording, or robot execution experiment.\n')
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                space = area.spaces.active
                space.overlay.show_overlays = False
                space.shading.type = 'MATERIAL'
                space.clip_end = 1000
                space.region_3d.view_perspective = 'CAMERA'
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / 'cave_showcase.blend'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', required=True)
    parser.add_argument('--samples', type=int, default=80)
    parser.add_argument('--only', type=int, nargs='+')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    render(args.folder, args.samples, args.only)
