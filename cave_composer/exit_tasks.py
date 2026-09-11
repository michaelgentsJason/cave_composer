"""Offline geometric acceptance of entrance-to-exit traces; no policy result."""
import numpy as np
from matplotlib.path import Path as PolygonPath
from .planning import certify_polyline
from .portals import surface_path_certificate


def _crossings(points, portal, loop, entering, safety):
    p=np.asarray(portal['center']);n=np.asarray(portal['inward']);v=np.asarray(loop['vertices'])
    tangent=np.cross(n,[0,0,1.]);tangent/=np.linalg.norm(tangent);up=np.cross(n,tangent)
    frame=np.column_stack([tangent,up]);poly=(v-p)@frame
    for i,(a,b) in enumerate(zip(points[:-1],points[1:])):
        da,db=(a-p)@n,(b-p)@n
        if not ((da<0<=db) if entering else (da>=0>db)):continue
        q=a+(b-a)*(-da)/(db-da);xy=(q-p)@frame
        edges=np.roll(poly,-1,axis=0)-poly
        f=np.clip(np.sum((xy-poly)*edges,axis=1)/np.maximum(np.sum(edges*edges,axis=1),1e-30),0,1)
        margin=np.linalg.norm(xy-poly-f[:,None]*edges,axis=1).min()
        if PolygonPath(poly).contains_point(xy) and margin>safety:yield i,q


def certify_exit_trace(points, references, surfaces, portal_report, safety=.55, goal_tolerance=.5):
    """To evaluate policy success, ALSO require valid timestamps/no collisions/budget.

    Uses privileged geometry offline. Calling it with a planned witness validates
    a task only and must never be reported as a completed policy episode.
    """
    points=np.asarray(points,dtype=float)
    if points.ndim!=2 or points.shape[1]!=3 or len(points)<2 or not np.isfinite(points).all():raise ValueError('Finite 3D trace required')
    portals=portal_report['portals'];loops=portal_report['meshes']['collision']['boundary_loops']
    entrance=next(l for l in loops if l['name']=='entrance');exit_loop=next(l for l in loops if l['name']=='exit')
    entries=list(_crossings(points,portals[0],entrance,True,safety));exits=list(_crossings(points,portals[1],exit_loop,False,safety))
    pairs=[(a,b) for a in entries for b in exits if b[0]>=a[0]]
    if not pairs:return {'status':'FAIL','reason':'missing_ordered_aperture_crossings'}
    if np.linalg.norm(points[-1]-portals[1]['outside_point'])>goal_tolerance:return {'status':'FAIL','reason':'goal_not_reached'}
    (ia,a),(ib,b)=pairs[0]
    interior=np.vstack([a,points[ia+1:ib+1],b])
    checks={kind:{'closed_interior':certify_polyline(references[kind],interior,safety),
                  'open_trace':surface_path_certificate(surfaces[kind],points,safety)} for kind in ['visual','collision']}
    good=all(c['status']=='PASS' for k in checks.values() for c in k.values())
    return {'status':'PASS' if good else 'FAIL','reason':None if good else 'trace_geometry_rejected',
            'checks':checks,'entrance_segment':ia,'exit_segment':ib,
            'scope':'Geometric ordered aperture crossing and goal proximity; no execution, time or dynamics evidence.'}
