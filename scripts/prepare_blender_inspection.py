"""Build a textured interactive Blender inspection scene from portal export.

Run with Blender --background --python this_file -- --scene PORTAL_EXPORT.
Frames 1 / 40 / 80 / 120 select entrance / interior / exit / overview cameras.
"""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cave_composer.blender_render import aim, light, material


def prepare(folder, render=True):
    folder = Path(folder).resolve()
    report = json.loads((folder / 'metadata/portal_validation.json').read_text())
    if report['status'] != 'PASS':
        raise ValueError('Portal geometry must pass validation first')
    nav = json.loads((folder / 'navigation/centerline.json').read_text())
    points = np.asarray(nav['routes'][0]['points'])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = 'Cave - entrance, chambers, exit'
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32
    scene.cycles.preview_samples = 16
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
    scene.render.resolution_x = 1440
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    scene.world = bpy.data.worlds.new('Neutral exterior - inspection lighting')
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes['Background']
    bg.inputs[0].default_value = (.52, .65, .78, 1)
    bg.inputs[1].default_value = .45
    meshes = {}
    rock = material(folder)
    rock.name = 'Sandstone - original procedural albedo and bump'
    for kind in ['visual', 'collision']:
        data = np.load(folder / kind / 'mesh.npz')
        mesh = bpy.data.meshes.new(kind + ' - two real terminal openings')
        mesh.from_pydata(data['vertices'].tolist(), [], data['faces'].tolist())
        mesh.update()
        obj = bpy.data.objects.new('Cave ' + kind + ' - OPEN entrance and exit', mesh)
        bpy.context.collection.objects.link(obj)
        if kind == 'visual':
            obj.data.materials.append(rock)
            for poly in mesh.polygons:
                poly.use_smooth = True
            vertices = data['vertices']
        else:
            obj.hide_render = True
            obj.hide_viewport = True
            obj.display_type = 'WIRE'
        meshes[kind] = obj

    # Work lights aid inspection. They are not a simulated underwater sensor rig.
    for i in range(6, len(points) - 4, 18):
        light('Inspection work light %03d' % i, points[i] + [0, 0, .5], 85, .55)
    for portal in report['portals']:
        center, normal = np.array(portal['center']), np.array(portal['inward'])
        light(portal['name'].title() + ' exterior softbox', center - normal * 5 + [0, 0, 2],
              900, 5, color=(.8, .89, 1), target=center)
    first, last = report['portals']
    p0, n0 = np.array(first['center']), np.array(first['inward'])
    p1, n1 = np.array(last['center']), np.array(last['inward'])
    index = int(len(points) * .37)
    light('Interior inspection key', points[max(0, index - 2)] + [0, 0, .25], 430, .6)
    light('Interior inspection fill', points[index + 4] + [0, 0, .45], 160, .8)
    center = (vertices.min(0) + vertices.max(0)) / 2
    extent = float(np.max(np.ptp(vertices, axis=0)))
    views = [
        (1, '01 Entrance - looking outside', p0 + n0 * 4, p0 - n0 * 5, 'entrance.png'),
        (40, '02 Interior - sandstone chamber', points[index], points[index + 18], 'interior.png'),
        (80, '03 Exit - looking outside', p1 + n1 * 4, p1 - n1 * 5, 'exit.png'),
        (120, '04 Overview - intact cave', center + [0, -extent * 1.3, extent * 1.4], center, 'overview.png'),
        (160, '05 Entrance - outside looking in', p0 - n0 * 6 + [0, 0, .5], p0 + n0 * 8, 'entrance_outside.png'),
    ]
    cameras = {}
    for frame, name, position, target, filename in views:
        data = bpy.data.cameras.new(name)
        data.lens = 19 if frame != 120 else 42
        data.clip_start, data.clip_end = .05, 1000
        cam = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(cam)
        cam.location = position
        aim(cam, target)
        marker = scene.timeline_markers.new(name, frame=frame)
        marker.camera = cam
        cameras[frame] = cam
    scene.frame_start, scene.frame_end = 1, 160
    scene.render.fps = 24
    scene['inspection_guide'] = 'Frames: 1 Entrance | 40 Interior | 80 Exit | 120 Overview | 160 Outside entrance. Numpad 0 camera view; Shift+` walk.'
    scene['geometry_note'] = 'Both actual meshes have two openings. No preview-only cap hiding. Original v0.3 bundle retained separately.'
    scene['lighting_note'] = 'Neutral material inspection with work lights. No water, scattering, or robot simulator.'
    text = bpy.data.texts.new('READ ME - camera frames and geometry')
    text.write('CAVE COMPOSER - OPEN PORTAL INSPECTION\n\n'
               'Frame 1: entrance, looking from inside to outside\n'
               'Frame 40: sandstone chamber and wall texture\n'
               'Frame 80: exit, looking from inside to outside\n'
               'Frame 120: intact whole cave, no roof cutaway\n\n'
               'Frame 160: entrance from outside looking into the cave\n\n'
               'Set the current frame in the Timeline to switch cameras.\n'
               'Numpad 0: camera view. Shift+`: walk mode, WASD move, Q/E down/up.\n'
               'If that shortcut differs on your keymap, use View > Navigation > Walk Navigation.\n\n'
               'Open visual and collision meshes are actual exported geometry.\n'
               'Collision object is hidden by default. No missing ceiling preview trick.\n'
               'Texture is procedural sandstone, not a scanned CAVERS surface.\n'
               'Inspection uses neutral lighting and additional work lights.\n'
               'This is an open shell, without exterior terrain or solid rock thickness.\n'
               'Portal validation: ' + str(folder / 'metadata/portal_validation.json') + '\n')
    for frame, name, position, target, filename in views:
        if not render:
            break
        scene.frame_set(frame)
        scene.camera = cameras[frame]
        scene.render.filepath = str(folder / 'previews' / filename)
        bpy.ops.render.render(write_still=True)
    scene.frame_set(40)
    scene.camera = cameras[40]
    bpy.context.view_layer.objects.active = meshes['visual']
    meshes['visual'].select_set(True)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                space = area.spaces.active
                space.overlay.show_overlays = False
                space.shading.type = 'RENDERED'
                space.clip_start, space.clip_end = .05, 1000
                space.region_3d.view_perspective = 'CAMERA'
                space.region_3d.view_camera_zoom = 0
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / 'cave_open_inspection.blend'))
    (folder / 'metadata/inspection_render.json').write_text(json.dumps({
        'blender': bpy.app.version_string, 'engine': scene.render.engine, 'device': scene.cycles.device,
        'texture': 'original procedural sandstone albedo, box projection, procedural bump',
        'neutral_water_free': True, 'frames': {str(f): name for f, name, *_ in views},
        'default_frame': 40, 'geometry': 'actual open portal meshes, no roof cutaway'}, indent=2), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene', required=True)
    parser.add_argument('--no-render', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    prepare(args.scene, render=not args.no_render)
