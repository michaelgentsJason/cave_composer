"""Run with Blender --background --python ... -- scene_paths to inspect packed bundles."""
import argparse
import json
import sys
from pathlib import Path
import bpy

parser = argparse.ArgumentParser()
parser.add_argument('scenes', nargs='+')
parser.add_argument('--output', required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
results = []
for value in args.scenes:
    folder = Path(value).resolve()
    bpy.ops.wm.open_mainfile(filepath=str(folder/'cave.blend'))
    obj = bpy.data.objects['Cave visual']
    metrics = json.loads((folder/'metadata/metrics.json').read_text())
    assert len(obj.data.polygons) == metrics['visual_triangles'], 'Saved blend is not the intact visual mesh'
    textures = [image for image in bpy.data.images if image.source=='FILE']
    assert textures and all(image.packed_file for image in textures), 'External unpacked texture'
    assert not any(item.type=='CURVE' for item in bpy.data.objects), 'Cutaway route overlay remains'
    results.append({'scene':folder.name,'full_visual_mesh':True,'packed_textures':len(textures),'status':'PASS'})
Path(args.output).write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps(results))
