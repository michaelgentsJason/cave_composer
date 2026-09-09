"""Blender stereo RGB interface smoke test on a verified task pack.

Paired cameras share a single body pose, lighting, exposure and scene state.
Output is separate from the immutable task pack.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
import numpy as np
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cave_composer.blender_render import material, light


def render(pack, output, number=3):
    pack, output = Path(pack).resolve(), Path(output).resolve()
    if output.exists() or pack in output.parents or output in pack.parents:
        raise ValueError('Use a new stereo output separate from task pack')
    checks = json.loads((pack/'metadata/checksums.json').read_text())
    actual = {p.relative_to(pack).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in pack.rglob('*') if p.is_file() and p != pack/'metadata/checksums.json'}
    if checks != actual:
        raise ValueError('Task pack changed')
    rig = json.loads((pack/'stereo_rig.json').read_text())
    all_episodes = json.loads((pack/'episodes.json').read_text())['episodes']
    episodes = [e for e in all_episodes if e['id'] in ['task_0001', 'task_0003', 'task_0007']][:number]
    if not episodes:
        episodes = all_episodes[:number]
    if not episodes:
        raise ValueError('No certified episodes')
    output.mkdir(parents=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 48
    scene.cycles.use_denoising = True
    prefs = bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type = 'OPTIX'
        prefs.get_devices()
        for device in prefs.devices:
            device.use = device.type == 'OPTIX'
        if any(d.use for d in prefs.devices):
            scene.cycles.device = 'GPU'
    except Exception:
        pass
    scene.render.resolution_x, scene.render.resolution_y = rig['resolution']
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.pixel_aspect_x = scene.render.pixel_aspect_y = 1
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.exposure = 0
    scene.world = bpy.data.worlds.new('Dark cave')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .003
    data = np.load(pack/'visual/mesh.npz')
    mesh = bpy.data.meshes.new('Verified cave')
    mesh.from_pydata(data['vertices'].tolist(), [], data['faces'].tolist())
    mesh.update()
    obj = bpy.data.objects.new('Verified cave', mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(material(pack))
    for poly in mesh.polygons:
        poly.use_smooth = True
    lamps = [light('Body work light', [0, 0, 0], 400, .35),
             light('Body fill', [0, 0, 0], 85, .8, color=(.85, .9, 1.))]
    cameras = {}
    for side in ['left', 'right']:
        camdata = bpy.data.cameras.new(side)
        camdata.sensor_fit = 'HORIZONTAL'
        camdata.sensor_width = 36
        camdata.lens = rig['cameras'][side]['K'][0][0]*36/rig['resolution'][0]
        camdata.clip_start, camdata.clip_end = .04, 200
        cam = bpy.data.objects.new(side, camdata)
        bpy.context.collection.objects.link(cam)
        cameras[side] = cam
    results = []
    for episode in episodes:
        rotation = np.asarray(Quaternion(episode['start']['orientation_wxyz']).to_matrix())
        world_body = np.eye(4)
        world_body[:3, :3] = rotation
        world_body[:3, 3] = episode['start']['position_m']
        for lamp, offset in zip(lamps, [[0., 0., .2], [.6, 0., .1]]):
            lamp.location = rotation @ offset + world_body[:3, 3]
        entry = {'id': episode['id'], 'body_pose': world_body.tolist(), 'images': {}, 'camera_world_matrices': {}}
        projection = {}
        probes = np.array([[3., -.4, -.2], [5., 0., 0.], [8., .7, .4]])
        for side, cam in cameras.items():
            transform = world_body @ np.array(rig['cameras'][side]['T_body_from_optical']) @ np.diag([1., -1., -1., 1.])
            cam.matrix_world = Matrix(transform.tolist())
            bpy.context.view_layer.update()
            scene.camera = cam
            projection[side] = []
            errors = []
            extr = np.asarray(rig['cameras'][side]['T_body_from_optical'])
            K = np.asarray(rig['cameras'][side]['K'])
            for point in probes:
                world = rotation @ point + world_body[:3, 3]
                uv = world_to_camera_view(scene, cam, Vector(world))
                pixel = np.array([uv.x*rig['resolution'][0], (1-uv.y)*rig['resolution'][1]])
                optical = (point-extr[:3, 3]) @ extr[:3, :3]
                projected = K @ optical
                errors.append(float(np.linalg.norm(pixel-projected[:2]/projected[2])))
                projection[side].append(pixel.tolist())
            if max(errors) > .02:
                raise ValueError('Blender projection disagrees with exported K/extrinsics')
            entry.setdefault('max_projection_error_pixels', {})[side] = max(errors)
            entry['camera_world_matrices'][side] = transform.tolist()
            filename = episode['id']+'_'+side+'.png'
            scene.render.filepath = str(output/filename)
            bpy.ops.render.render(write_still=True)
            entry['images'][side] = filename
        disparity = np.asarray(projection['left'])-np.asarray(projection['right'])
        if np.max(np.abs(disparity[:, 1])) > .02 or np.any(disparity[:, 0] <= 0):
            raise ValueError('Stereo epipolar/disparity sign check failed')
        entry['maximum_vertical_disparity_pixels'] = float(np.max(np.abs(disparity[:, 1])))
        entry['disparity_test'] = 'Known 3D projection probes; not image-estimated correspondence accuracy'
        results.append(entry)
    report = {'status': 'PASS', 'pairs': results, 'rig': rig, 'source_pack_checksums_sha256': hashlib.sha256((pack/'metadata/checksums.json').read_bytes()).hexdigest(),
        'engine': 'Cycles', 'samples': 48, 'device': scene.cycles.device,
        'scope': 'Calibrated rendering-interface smoke test, not closed-loop navigation or water-optics validation.',
        'sensor_state': 'same pose/time, fixed exposure, shared illumination, no image flips, no depth export to actor'}
    (output/'stereo_verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'stereo_inspection.blend'))
    print('STEREO_INTERFACE_PASS', len(results))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    render(args.pack, args.output)
