import numpy as np


def ray_distances(mesh,origins,directions,limit=80):
    locations,rays,_=mesh.ray.intersects_location(origins,directions,multiple_hits=True)
    values=np.full(len(origins),float(limit))
    if len(locations):
        d=np.linalg.norm(locations-origins[rays],axis=1)
        d[d<1e-5]=limit
        np.minimum.at(values,rays,d)
    return values


def compute_metrics(spec,routes,graph,collision,clearance):
    main=routes[0]; points=main['points']; tangent=np.gradient(points,axis=0); tangent/=np.linalg.norm(tangent,axis=1)[:,None]
    indices=np.arange(5,len(points)-5,5)
    horizon=ray_distances(collision,points[indices],tangent[indices])
    # Furthest *consecutively* visible path sample within 90-degree horizontal cone.
    lookahead=[]
    for idx in indices:
        targets=np.arange(idx+3,min(len(points),idx+201),3)
        d=points[targets]-points[idx]; lengths=np.linalg.norm(d,axis=1); direction=d/lengths[:,None]
        hit=ray_distances(collision,np.tile(points[idx],(len(targets),1)),direction)
        visible=(hit+0.015>=lengths)&(direction@tangent[idx]>=np.cos(np.deg2rad(45)))
        bad=np.flatnonzero(~visible)
        count=int(bad[0]) if len(bad) else len(visible)
        lookahead.append(float(main['s'][targets[count-1]]-main['s'][idx]) if count else 0.)
    allpoints=np.concatenate([r['points'] for r in routes])
    angles=[e['angle_degrees'] for r in routes for e in r['events'] if e['type']=='turn']
    lengths=[float(r['s'][-1]) for r in routes]
    slopes=[]; curvatures=[]
    for r in routes:
        d=np.diff(r['points'],axis=0); norm=np.linalg.norm(d,axis=1); t=d/norm[:,None]
        slopes.extend(np.rad2deg(np.arctan2(np.abs(d[:,2]),np.linalg.norm(d[:,:2],axis=1))))
        curvatures.extend(np.arccos(np.clip((t[:-1]*t[1:]).sum(1),-1,1))/((norm[:-1]+norm[1:])/2))
    width=[]; height=[]
    for r in routes:
        ps=r['points'][5:-5:5]; ts=np.gradient(r['points'],axis=0)[5:-5:5]; ts/=np.linalg.norm(ts,axis=1)[:,None]
        side=np.cross(np.tile([0,0,1.],(len(ts),1)),ts); side/=np.linalg.norm(side,axis=1)[:,None]; up=np.cross(ts,side)
        width.extend(ray_distances(collision,ps,side)+ray_distances(collision,ps,-side))
        height.extend(ray_distances(collision,ps,up)+ray_distances(collision,ps,-up))
    result={'total_length':sum(lengths),'main_route_length':lengths[0], 'command_exact_length':sum(e['length'] for e in main['events']),
            'num_turns':len(angles),'turn_angles_degrees':angles,'max_turn_angle':max(map(abs,angles),default=0),
            'mean_curvature':float(np.mean(curvatures)),'max_curvature':float(max(curvatures)),
            'num_sharp_turns':sum(abs(a)>=60 for a in angles),'junction_count':len(graph['junctions']),
            'branch_count':len(routes)-1,'dead_end_count':sum(n['semantic_type']=='dead_end' for n in graph['nodes']),
            'loop_count':graph['cycle_rank'],'vertical_range':float(np.ptp(allpoints[:,2])), 'max_slope':float(max(slopes)),
            'mean_width':float(np.mean(width)),'minimum_width':float(min(width)), 'minimum_height':float(min(height)),
            'chamber_count':len(spec['chambers']),'topological_complexity':len(graph['junctions'])+2*graph['cycle_rank'],
            'minimum_mesh_clearance':float(clearance.min()),'mean_forward_visibility':float(horizon.mean()),
            'minimum_forward_visibility':float(horizon.min()),'mean_visible_route_lookahead':float(np.mean(lookahead)),
            'width_measurement':'paired wall rays on transverse section axes, every fifth route sample; excludes cap-adjacent samples',
            'turn_measurement':'command values; plan-view circular arc geometry; sampled arc chords slightly shorten total_length'}
    visibility={'s_metres':main['s'][indices].tolist(),'forward_ray_metres':horizon.tolist(),'visible_route_arc_metres':lookahead,
                'ray_max_range':80,'fov_degrees':90,'target_step_metres_approx':0.9,'origin_step_metres_approx':1.5,
                'model':'opaque geometry only, tangent ray plus contiguous visible route samples; no water model'}
    return result,visibility
