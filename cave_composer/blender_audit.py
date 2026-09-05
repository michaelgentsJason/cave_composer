"""Independent BVH nonadjacent triangle overlap audit of extracted meshes."""
import sys,json,argparse
from pathlib import Path
import numpy as np
from mathutils.bvhtree import BVHTree
import bpy

p=argparse.ArgumentParser(); p.add_argument('--scene',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]); folder=Path(a.scene)
result={'blender':bpy.app.version_string,'method':'BVHTree triangle overlap, shared-vertex pairs excluded; floating-point audit, not exact-predicate proof','meshes':{}}
for kind in ['visual','collision']:
    data=np.load(folder/kind/'mesh.npz'); vertices=data['vertices']; faces=data['faces']
    tree=BVHTree.FromPolygons(vertices.tolist(),faces.tolist(),all_triangles=True,epsilon=0)
    overlaps=tree.overlap(tree)
    bad=[]
    for i,j in overlaps:
        if i>=j: continue
        if not set(faces[i]).intersection(faces[j]): bad.append([int(i),int(j)])
    result['meshes'][kind]={'nonadjacent_intersecting_pairs':len(bad),'examples':bad[:20], 'triangles':len(faces)}
result['status']='PASS' if all(d['nonadjacent_intersecting_pairs']==0 for d in result['meshes'].values()) else 'FAIL'
(folder/'metadata/intersection_audit.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
if result['status']!='PASS': raise RuntimeError('Nonadjacent triangle intersections found')
