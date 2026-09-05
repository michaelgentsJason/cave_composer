"""Independent mesh distance checks and conservative occupancy connectivity evidence."""
import numpy as np
import trimesh
from scipy import ndimage
from skimage.measure import euler_number
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree


def mesh_clearance(mesh, points):
    distances=[]
    for start in range(0,len(points),100):
        _,d,_=trimesh.proximity.closest_point(mesh,points[start:start+100])
        distances.extend(d)
    return np.asarray(distances)


def shortcut_audit(graph,mesh,safety,max_width):
    """Detect robot-clear direct connections between graph-distant route samples.

    Local corner cutting and paths around individual wall formations are allowed;
    this is not an exact recovered medial-axis graph isomorphism test.
    """
    p=np.asarray([n['position'] for n in graph['nodes']]); n=len(p)
    rows=[]; cols=[]; values=[]
    for e in graph['edges']:
        rows.extend([e['source'],e['target']]); cols.extend([e['target'],e['source']]); values.extend([e['length']]*2)
    adjacency=csr_matrix((values,(rows,cols)),shape=(n,n))
    selected=np.arange(0,n,5); samples=p[selected]
    distance=dijkstra(adjacency,directed=False,indices=selected)
    pairs=sorted(cKDTree(samples).query_pairs(max_width*1.5))
    candidates=[]
    for a,b in pairs:
        direct=np.linalg.norm(samples[a]-samples[b]); route=distance[a,selected[b]]
        if direct>0.1 and route>max(10.,2.2*direct+5): candidates.append((a,b,direct,float(route)))
    bad=[]
    for a,b,direct,route in candidates:
        # Clearance along the whole connector, using distance's 1-Lipschitz bound.
        q=np.linspace(samples[a],samples[b],max(3,int(np.ceil(direct/0.35))+1))
        if not np.all(mesh.contains(q)): continue
        clearance=mesh_clearance(mesh,q).min()-direct/(len(q)-1)/2
        if clearance>safety:
            bad.append({'a':int(selected[a]),'b':int(selected[b]),'direct_metres':float(direct),'graph_metres':route,'clearance_lower_bound':float(clearance)})
    return {'status':'PASS' if not bad else 'FAIL','sample_stride':5,'candidate_pairs':len(candidates),'shortcuts':bad[:30],
            'definition':'direct robot-clear connector with graph distance > max(10 m, 2.2 * Euclidean distance + 5 m)',
            'limitations':'sampled local connector test; curved shortcuts and exact homotopy equivalence are not certified'}


def validate(spec, routes, graph, field, visual, collision, grid, origin):
    points=np.concatenate([r['points'] for r in routes])
    step=max(float(np.linalg.norm(np.diff(r['points'],axis=0),axis=1).max()) for r in routes)
    safety=spec['robot']['radius']+spec['robot']['margin']
    report={'status':'INVALID','robot_safety_radius':safety,'path_sample_max_step':step,'checks':{},'mesh':{}}
    checks=report['checks']
    clearances={}
    for name,mesh in [('visual',visual),('collision',collision)]:
        distances=mesh_clearance(mesh,points)
        lower=float(distances.min()-step/2)
        tri=mesh.triangles_center
        select=np.linspace(0,len(tri)-1,min(8000,len(tri)),dtype=int)
        normals=mesh.face_normals[select]
        normal_sign=field(tri[select]+normals*0.04)-field(tri[select]-normals*0.04)
        entry={'vertices':len(mesh.vertices),'triangles':len(mesh.faces),'watertight':bool(mesh.is_watertight),
               'winding_consistent':bool(mesh.is_winding_consistent),'inward_signed_volume':float(mesh.volume),
               'min_triangle_area':float(mesh.area_faces.min()),'finite':bool(np.isfinite(mesh.vertices).all()),
               'minimum_sampled_clearance':float(distances.min()),'continuous_polyline_clearance_lower_bound':lower,
               'inward_normal_fraction':float(np.mean(normal_sign>0)), 'bounds_metres':mesh.bounds.tolist(),
               'self_intersection':'regular-grid Lewiner construction; separate Blender BVH audit pending'}
        report['mesh'][name]=entry
        checks[name+'_mesh_sanity']=entry['watertight'] and entry['winding_consistent'] and entry['finite'] and entry['min_triangle_area']>1e-10
        checks[name+'_inward_normals']=entry['inward_signed_volume']<0 and entry['inward_normal_fraction']>0.98
        checks[name+'_route_clearance']=lower>safety
        # Inside/outside is not inferred from unsigned proximity alone.
        checks[name+'_route_inside']=bool(np.all(mesh.contains(points)))
        clearances[name]=distances
    voxel=spec['mesh']['collision_voxel']
    free=grid>0
    labels,count=ndimage.label(free)
    indices=np.rint((points-origin)/voxel).astype(int)
    indices=np.clip(indices,0,np.array(free.shape)-1)
    route_labels=labels[tuple(indices.T)]
    checks['free_space_connected']=count==1 and np.all(route_labels>0)
    # Subtract half the voxel diagonal to bound distance from a free node to any
    # point in a solid cell. This is discrete occupancy evidence, independently
    # backed by the continuous mesh-to-polyline certificate above.
    edt=ndimage.distance_transform_edt(free,sampling=voxel)
    safe=edt-voxel*np.sqrt(3)/2>safety
    safe_labels,safe_count=ndimage.label(safe)
    witnesses=safe_labels[tuple(indices.T)]
    checks['robot_space_route_connected']=bool(np.all(witnesses>0) and len(np.unique(witnesses))==1)
    topology_euler=int(euler_number(free,connectivity=1))
    safe_main=safe_labels==int(witnesses[0]) if witnesses[0]>0 else np.zeros_like(safe)
    safe_euler=int(euler_number(safe_main,connectivity=1))
    # Rock shelves can create sub-robot handles in the raw void. Compare the
    # robot-sized component's cycle rank, not every geological micro-hole.
    report['topology_diagnostics']={'robot_euler_matches_semantic_graph':safe_euler==1-graph['cycle_rank'],
        'interpretation':'Local paths around rock shelves may add handles. Euler characteristic is diagnostic, not semantic graph equality.'}
    shortcuts=shortcut_audit(graph,collision,safety,spec['corridor']['width'])
    checks['no_sampled_nonlocal_shortcuts']=shortcuts['status']=='PASS'
    report['shortcut_audit']=shortcuts
    slopes=[]
    for r in routes:
        d=np.diff(r['points'],axis=0)
        slopes.extend(np.rad2deg(np.arctan2(np.abs(d[:,2]),np.linalg.norm(d[:,:2],axis=1))))
    max_slope=float(max(slopes))
    checks['slope_limit']=max_slope<=spec['validation']['max_slope_degrees']+1e-6
    checks['bounds_finite']=bool(np.isfinite(collision.bounds).all())
    report['voxel']={'size':voxel,'shape':list(grid.shape),'free_components':int(count),'eroded_components':int(safe_count),
                     'euler_characteristic':topology_euler,'robot_component_euler':safe_euler,'expected_robot_euler':1-graph['cycle_rank'],
                     'minimum_route_edt_lower_bound':float((edt[tuple(indices.T)]-voxel*np.sqrt(3)/2).min())}
    report['repairs']=getattr(field,'repairs',{})
    report['max_slope_degrees']=max_slope
    report['limitations']=['Voxel topology does not locate every unintended shortcut; equal Euler characteristic is not graph isomorphism.',
                          'Clearance certificate applies to spherical robot swept along sampled polylines; dynamics and tracking error beyond the margin are not modeled.',
                          'Robust self-intersection audit requires the optional Blender BVH stage.']
    report['checks']={k:bool(v) for k,v in checks.items()}
    report['status']='VALID' if all(checks.values()) else 'INVALID'
    return report,clearances
