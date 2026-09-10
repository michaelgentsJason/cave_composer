"""Paired mesh-section diagnostics; no scalar realism score or real-data fitting."""
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as PolygonPath
import numpy as np
from scipy.spatial import ConvexHull
import trimesh

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cave_composer.routes import build_routes


def sections(folder):
    spec=json.loads((folder/'metadata/config.json').read_text())
    route=build_routes(spec)[0]
    with np.load(folder/'visual/mesh.npz') as data:
        mesh=trimesh.Trimesh(data['vertices'],data['faces'],process=False)
    records=[]
    for fraction in np.linspace(.10,.9,41):
        i=round((len(route['points'])-1)*fraction)
        point=route['points'][i];tangent=route['points'][i+1]-route['points'][i-1]
        tangent/=np.linalg.norm(tangent);side=np.cross([0,0,1],tangent);side/=np.linalg.norm(side)
        up=np.cross(tangent,side)
        section=mesh.section(plane_origin=point,plane_normal=tangent)
        candidates=[]
        for curve in section.discrete if section is not None else []:
            if np.linalg.norm(curve[0]-curve[-1])>1e-5:continue
            xy=(curve-point)@np.column_stack([side,up])
            if not PolygonPath(xy).contains_point((0,0)):continue
            p,q=xy[:-1],xy[1:];cross=p[:,0]*q[:,1]-q[:,0]*p[:,1]
            signed=cross.sum()/2
            if abs(signed)<1e-6:continue
            centroid=((p+q)*cross[:,None]).sum(0)/(6*signed)
            area=abs(signed);hull=ConvexHull(p).volume
            candidates.append({'s':float(route['s'][i]),'fraction':float(fraction),'area_m2':float(area),
                               'nonconvexity':float(1-area/hull),
                               'eccentricity':float(np.linalg.norm(centroid)/np.sqrt(area/np.pi)),
                               'contour':xy.tolist()})
        if not candidates:raise RuntimeError(f'No closed origin-containing section at {folder}/{fraction}')
        # Select local enclosing cavity; not a reconstruction of global passage topology.
        records.append(min(candidates,key=lambda r:r['area_m2']))
    areas=np.array([r['area_m2'] for r in records]);arc=np.array([r['s'] for r in records])
    return {'sections':records,'summary':{'area_cv':float(areas.std()/areas.mean()),
        'mean_nonconvexity':float(np.mean([r['nonconvexity'] for r in records])),
        'mean_normalized_eccentricity':float(np.mean([r['eccentricity'] for r in records])),
        'max_section_area_gradient_m2_per_m':float(np.max(np.abs(np.diff(areas)/np.diff(arc))))}}


def main(root='outputs/morphology_v01'):
    root=Path(root);records={}
    names=['before','after','section_only','roughness_only','features_only','rockfall_only']
    for name in names:
        records[name]=sections(root/name)
        metrics=json.loads((root/name/'metadata/metrics.json').read_text())
        records[name]['summary'].update({k:metrics[k] for k in ['mean_forward_visibility','mean_visible_route_lookahead',
             'planned_path_clearance','generation_seconds','visual_triangles','collision_triangles']})
        print(name,records[name]['summary'],flush=True)
    result={'method':'41 matched transverse planes on final visual meshes; local enclosing contour only; same layout, seeds and material',
            'limitations':['No real-cave distribution comparison','Section contours exclude separate obstacle holes',
                           'Visibility is the existing opaque collision-mesh diagnostic, not sensor or policy performance'],
            'cases':records}
    (root/'morphology_measurements.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    with plt.rc_context({'font.family':'DejaVu Sans','font.size':11}):
        fig,axes=plt.subplots(1,4,figsize=(15,3.5),layout='constrained')
        for ax,fraction,label in zip(axes[:3],[.36,.5,.74],['Wall overhang','Ceiling drop','Rockfall region']):
            for name,color in [('before','#71828b'),('after','#168c9e')]:
                r=min(records[name]['sections'],key=lambda r:abs(r['fraction']-fraction));xy=np.array(r['contour'])
                ax.plot(*xy.T,color=color,lw=1.6,label=name.capitalize())
            ax.add_patch(plt.Circle((0,0),.55,color='#b64282',fill=False,ls='--',lw=1))
            ax.set(aspect='equal',xlabel='Lateral / m',ylabel='Vertical / m',title=label)
            ax.spines[['top','right']].set_visible(False)
        axes[0].legend(frameon=False,fontsize=9)
        for name,color in [('before','#71828b'),('after','#168c9e')]:
            r=records[name]['sections'];axes[3].plot([p['s'] for p in r],[p['area_m2'] for p in r],color=color,label=name)
        axes[3].set(xlabel='Main-route distance / m',ylabel='Section area / m²',title='Along-passage variation')
        axes[3].spines[['top','right']].set_visible(False)
        fig.savefig(root/'section_comparison.png',dpi=220)
        fig.savefig(root/'section_comparison.svg')
        plt.close(fig)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--root',default='outputs/morphology_v01')
    main(p.parse_args().root)
