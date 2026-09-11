"""Blender: inspect crop boundaries and possible path extensions to cut planes.

This checks observed triangles only; open scan holes do not become free-space
evidence. It is deliberately separate from closed procedural-cave validation.
"""
import json
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path('exports/metashape_crops_v01')


def inspect(name):
    folder=ROOT/name;d=np.load(folder/'source_crop.npz');v=d['vertices'];f=d['faces']
    bounds=np.array(json.loads((folder/'metadata.json').read_text())['plan']['bounds'])
    route=np.array(json.loads((folder/'route.json').read_text())['points'])
    previous=json.loads((folder/'route_check.json').read_text())
    tree=BVHTree.FromPolygons(v.tolist(),f.tolist(),all_triangles=True,epsilon=0)
    # Weld clipping seams for boundary counting. The tolerance is explicit.
    _,weld=np.unique(np.round(v.astype(float)/1e-5).astype(np.int64),axis=0,return_inverse=True)
    wf=weld[f];edges=np.concatenate([wf[:,[0,1]],wf[:,[1,2]],wf[:,[2,0]]]);edges.sort(axis=1)
    _,counts=np.unique(edges,axis=0,return_counts=True)
    cut_counts={}
    for axis in range(3):
        for side in range(2):
            on=np.abs(v[:,axis]-bounds[side,axis])<1e-5
            cut_counts[f'{"XYZ"[axis]}_{"min" if side==0 else "max"}']=int(np.count_nonzero(on[f].sum(1)>=2))
    def extension(endpoint,tangent):
        tangent=tangent/np.linalg.norm(tangent)
        directions=[tangent]+[np.eye(3)[i]*s for i in range(3) for s in [-1,1]]
        for strength in [.35,.7]:
            directions += [tangent+strength*np.eye(3)[i]*s for i in range(3) for s in [-1,1]]
        candidates=[]
        for direction in directions:
            direction=direction/np.linalg.norm(direction)
            intersections=[]
            for axis in range(3):
                if abs(direction[axis])<1e-8:continue
                side=int(direction[axis]>0);t=(bounds[side,axis]-endpoint[axis])/direction[axis]
                if t>0:intersections.append((float(t),axis,side))
            length,axis,side=min(intersections)
            if cut_counts[f'{"XYZ"[axis]}_{"min" if side==0 else "max"}']==0:continue
            # Check a segment that actually crosses the spatial crop boundary.
            length+=.1;h=length/max(1,int(np.ceil(length/.03)))
            points=endpoint+np.linspace(0,length,int(round(length/h))+1)[:,None]*direction
            distances=np.array([tree.find_nearest(Vector(p))[3] for p in points])
            bound=float(distances.min()-h/2)
            if bound<=0:continue
            candidates.append({'points':points.tolist(),'length_model_units':length,'sample_spacing':h,
                'surface_distance_lower_bound':bound,'crossed_plane':f'{"XYZ"[axis]}_{"min" if side==0 else "max"}',
                'outward_alignment':float(direction@tangent)})
        if not candidates:return None
        return min(candidates,key=lambda c:c['length_model_units']+2*(1-c['outward_alignment']))
    first=extension(route[0],route[0]-route[min(8,len(route)-1)])
    last=extension(route[-1],route[-1]-route[max(0,len(route)-9)])
    report={'asset':name,'scale_status':'unverified_model_units','boundary_weld_tolerance':1e-5,
        'boundary_edges_after_welding':int(np.count_nonzero(counts==1)),
        'nonmanifold_edges_after_welding':int(np.count_nonzero(counts>2)),
        'triangles_with_edges_on_crop_planes':cut_counts,'crop_caps_added':False,
        'existing_candidate_path_length_model_units':previous['path_length_model_units'],
        'existing_candidate_surface_distance_lower_bound':previous['surface_clearance_lower_bound'],
        'start_extension':first,'goal_extension':last,
        'both_endpoints_connected_to_crop_exterior_without_observed_triangle_contact':first is not None and last is not None,
        'physical_navigation_certified':False,
        'limitations':['Open boundaries include original scan holes, not only deliberate crop openings.',
                      'Endpoint extensions are local geometric tests against recorded triangles, not independent inside-cave planning.',
                      'Metric scale, complete walls and a physical robot envelope remain unverified.']}
    if first is not None and last is not None:
        through=np.concatenate([np.array(first['points'])[::-1],route[1:],np.array(last['points'])[1:]])
        (folder/'crossing_candidate_route.json').write_text(json.dumps({'points':through.tolist(),
            'units':'unverified_model_units','coordinate_frame':'normalized source Z-up',
            'status':'observed-triangle clearance only; not an inside/free-space certificate',
            'surface_distance_lower_bound':min(first['surface_distance_lower_bound'],last['surface_distance_lower_bound'],previous['surface_clearance_lower_bound'])},indent=2),encoding='utf-8')
    (folder/'opening_check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(name,'boundary edges',report['boundary_edges_after_welding'],'extensions',
          [(e['crossed_plane'],e['surface_distance_lower_bound']) if e else None for e in [first,last]],flush=True)


if __name__=='__main__':
    for name in ['zhaoqing_validation_short','catacombs_validation_short']:inspect(name)
