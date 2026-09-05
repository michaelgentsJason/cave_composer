from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import time
import uuid
import numpy as np
import yaml
from .spec import load_spec
from .routes import build_routes,navigation_graph,junction_graph
from .field import CaveField
from .materials import write_material
from .export import write_obj
from .validation import validate
from .metrics import compute_metrics
from .previews import topology_preview


def dump(path,data):
    Path(path).write_text(json.dumps(data,indent=2,allow_nan=False,ensure_ascii=False)+'\n',encoding='utf-8')


def digest(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def mesh_digest(mesh):
    h=hashlib.sha256()
    h.update(np.asarray(mesh.vertices,dtype='<f8').tobytes()); h.update(np.asarray(mesh.faces,dtype='<i8').tobytes())
    return h.hexdigest()


def generate(config,seed=42,output=None,render=False,blender=None,save_blend=False):
    if isinstance(seed,bool) or int(seed)!=seed or seed<0: raise ValueError('seed must be a nonnegative integer')
    spec=load_spec(config)
    target=Path(output or Path('outputs')/f"{spec['name']}_{seed:06d}").resolve()
    if target.exists(): raise FileExistsError(f'Refusing to overwrite existing scene: {target}')
    target.parent.mkdir(parents=True,exist_ok=True)
    temp=target.with_name('.'+target.name+'.building-'+uuid.uuid4().hex[:8]); temp.mkdir()
    (temp/'.cave_composer_bundle').write_text('1\n')
    for name in ['visual','collision','materials','navigation','metadata','previews']: (temp/name).mkdir()
    started=time.perf_counter(); timings={}
    try:
        routes=build_routes(spec); field=CaveField(spec,routes,int(seed))
        graph=navigation_graph(routes,field.chamber_records,spec['bottlenecks'])
        dump(temp/'metadata/config.json',spec)
        (temp/'metadata/config.yaml').write_text(yaml.safe_dump(spec,sort_keys=False),encoding='utf-8')
        dump(temp/'navigation/navigation_graph.json',graph)
        dump(temp/'navigation/junction_graph.json',junction_graph(graph))
        dump(temp/'navigation/centerline.json',{'routes':[{'id':r['id'],'points':r['points'].tolist(),'s_metres':r['s'].tolist(),'widths_nominal':r['widths'].tolist(),'heights_nominal':r['heights'].tolist(),'events':r['events']} for r in routes]})
        main=routes[0]['points']; a=min(6,len(main)//4); b=max(a+1,len(main)-7)
        direction=main[a+1]-main[a]; direction/=np.linalg.norm(direction)
        dump(temp/'navigation/spawn_points.json',[{'position':main[a].tolist(),'forward':direction.tolist(),'up':[0,0,1],'robot_radius':spec['robot']['radius'],'safety_margin':spec['robot']['margin']}])
        dump(temp/'navigation/goals.json',[{'position':main[b].tolist(),'tolerance_metres':0.5}])
        t=time.perf_counter(); visual,_,_=field.mesh(spec['mesh']['visual_voxel']); collision,grid,origin=field.mesh(spec['mesh']['collision_voxel']); timings['geometry_seconds']=time.perf_counter()-t
        t=time.perf_counter(); validation,clearances=validate(spec,routes,graph,field,visual,collision,grid,origin); timings['validation_seconds']=time.perf_counter()-t
        dump(temp/'metadata/validation.json',validation)
        dump(temp/'navigation/clearance.json',{'visual':clearances['visual'].tolist(),'collision':clearances['collision'].tolist(),'ordering':'routes concatenated in centerline.json order'})
        t=time.perf_counter(); metrics,visibility=compute_metrics(spec,routes,graph,collision,clearances['collision']); timings['metrics_seconds']=time.perf_counter()-t
        metrics.update({'visual_triangles':len(visual.faces),'collision_triangles':len(collision.faces),'validation':validation['status']})
        dump(temp/'navigation/visibility_horizon.json',visibility)
        write_material(spec['material'],temp/'materials')
        write_obj(visual,temp/'visual/cave_visual.obj',visual=True); write_obj(collision,temp/'collision/cave_collision.obj')
        for name,mesh in [('visual',visual),('collision',collision)]: np.savez_compressed(temp/name/'mesh.npz',vertices=mesh.vertices,faces=mesh.faces)
        topology_preview(routes,graph,visibility,temp/'previews',spec['name'])
        geometry_spec={k:v for k,v in spec.items() if k not in ['name','description','material','split','ood_factors']}
        provenance={'composer_version':'0.1.0','seed':int(seed),'geometry_config_sha256':digest(geometry_spec),
                    'visual_mesh_sha256':mesh_digest(visual),'collision_mesh_sha256':mesh_digest(collision),
                    'appearance_sha256':digest(spec['material']),'platform':platform.platform(),'python':platform.python_version(),
                    'dependencies':{p:importlib.metadata.version(p) for p in ['numpy','scipy','scikit-image','trimesh','PyYAML']},
                    'geometry_source':'independent procedural level set; no scanned geometry',
                    'coordinates':'metres, right handed, Z up; cave boundary normals point into void',
                    'water_baked':False,'split':spec['split'],'generation':timings}
        provenance['source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob('*.py'))}
        timings['bundle_seconds_before_render']=time.perf_counter()-started
        if render:
            executable=blender or os.environ.get('BLENDER_PATH') or shutil.which('blender')
            if not executable: raise RuntimeError('Blender not found; pass --blender or set BLENDER_PATH')
            script=Path(__file__).resolve().parent/'blender_render.py'
            command=[str(executable),'--background','--python-exit-code','1','--python',str(script),'--','--scene',str(temp)]
            if save_blend: command.append('--save-blend')
            t=time.perf_counter()
            with (temp/'metadata/render.log').open('w',encoding='utf-8') as log:
                subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
            if not (temp/'previews/render_info.json').exists(): raise RuntimeError('Blender exited without completing all previews')
            audit_command=[str(executable),'--background','--python-exit-code','1','--python',str(Path(__file__).parent/'blender_audit.py'),'--','--scene',str(temp)]
            with (temp/'metadata/intersection_audit.log').open('w',encoding='utf-8') as log:
                subprocess.run(audit_command,stdout=log,stderr=subprocess.STDOUT,check=True)
            audit=json.loads((temp/'metadata/intersection_audit.json').read_text())
            validation['intersection_audit']=audit
            validation['checks']['bvh_no_nonadjacent_intersections']=audit['status']=='PASS'
            validation['status']='VALID' if all(validation['checks'].values()) else 'INVALID'
            metrics['validation']=validation['status']
            dump(temp/'metadata/validation.json',validation)
            timings['render_seconds']=time.perf_counter()-t
        timings['total_seconds']=time.perf_counter()-started
        metrics['generation_seconds']=timings['total_seconds']
        dump(temp/'metadata/metrics.json',metrics); dump(temp/'metadata/provenance.json',provenance)
        manifest={str(p.relative_to(temp)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(temp.rglob('*')) if p.is_file()}
        dump(temp/'metadata/checksums.json',manifest)
        temp.rename(target)
        if validation['status']!='VALID': raise ValueError(f"Scene INVALID; retained diagnostics at {target}: {[k for k,v in validation['checks'].items() if not v]}")
        return {'path':str(target),'status':validation['status'],'metrics':metrics}
    except Exception as exc:
        if temp.exists():
            dump(temp/'metadata/failure.json',{'error':type(exc).__name__,'message':str(exc)})
            failed=target.with_name(target.name+'.failed')
            if not failed.exists(): temp.rename(failed)
        raise
