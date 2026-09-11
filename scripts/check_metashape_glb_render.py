"""Blender import/render round trip for the textured scan export."""
import json,sys
from pathlib import Path
import bpy
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cave_composer.blender_render import aim

root=Path('exports/metashape_crops_v01').resolve()
for name in ['zhaoqing_validation_short','catacombs_train_long']:
    folder=root/name;bpy.ops.wm.open_mainfile(filepath=str(folder/'inspection.blend'))
    scene=bpy.context.scene
    view=json.loads((folder/'render_views.json').read_text())['views'][0]
    scene.camera.location=view['position'];aim(scene.camera,view['target'])
    scene.render.resolution_percentage=50
    scene.render.filepath=str(folder/'roundtrip_reference.png');bpy.ops.render.render(write_still=True)
    original=[o for o in scene.objects if o.type=='MESH']
    for obj in original:bpy.data.objects.remove(obj,do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=str(folder/'cave.glb'))
    meshes=[o for o in scene.objects if o.type=='MESH']
    assert sum(len(o.data.polygons) for o in meshes)==json.loads((folder/'metadata.json').read_text())['triangles']
    scene.render.filepath=str(folder/'roundtrip_glb.png');bpy.ops.render.render(write_still=True)
    print(name,'GLB_IMPORTED_AND_RENDERED',flush=True)
