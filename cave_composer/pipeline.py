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
from datetime import datetime,timezone
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
from .bundle import atomic_json,bundle_checksums,environment_signature


def dump(path,data):
    Path(path).write_text(json.dumps(data,indent=2,allow_nan=False,ensure_ascii=False)+'\n',encoding='utf-8')


def digest(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def mesh_digest(mesh):
    h=hashlib.sha256()
    h.update(np.asarray(mesh.vertices,dtype='<f8').tobytes()); h.update(np.asarray(mesh.faces,dtype='<i8').tobytes())
    return h.hexdigest()


def attach_intersection_audit(report,audit):
    """Attach the separate mesh audit without leaving a misleading pending label."""
    report['intersection_audit']=audit
    report['checks']['bvh_no_nonadjacent_intersections']=audit['status']=='PASS'
    for kind,details in audit['meshes'].items():
        report['mesh'][kind]['self_intersection']={
            'method':audit['method'],
            'nonadjacent_intersecting_pairs':details['nonadjacent_intersecting_pairs']}
    report['status']='VALID' if all(report['checks'].values()) else 'INVALID'


def generate(config,seed=42,output=None,render=False,blender=None,save_blend=False):
    if isinstance(seed,bool) or int(seed)!=seed or seed<0: raise ValueError('seed must be a nonnegative integer')
    spec=load_spec(config)
    if save_blend and not render: raise ValueError('save_blend requires render=True')
    executable=None
    if render:
        executable=blender or os.environ.get('BLENDER_PATH') or shutil.which('blender')
        executable=shutil.which(str(executable)) if executable else None
        if not executable: raise ValueError('Blender not found; pass --blender or set BLENDER_PATH')
    environment=environment_signature()
    target=Path(output or Path('outputs')/f"{spec['name']}_{seed:06d}").resolve()
    if target.exists(): raise FileExistsError(f'Refusing to overwrite existing scene: {target}')
    target.parent.mkdir(parents=True,exist_ok=True)
    temp=target.with_name('.'+target.name+'.building-'+uuid.uuid4().hex[:8]); temp.mkdir()
    (temp/'.cave_composer_bundle').write_text('1\n')
    for name in ['visual','collision','materials','navigation','metadata','previews']: (temp/name).mkdir()
    started=time.perf_counter(); timings={}
    run={'schema_version':1,'seed':int(seed),'config_sha256':digest(spec),
         'environment_sha256':digest(environment),'render':bool(render),'save_blend':bool(save_blend),
         'status':'RUNNING','started_utc':datetime.now(timezone.utc).isoformat(),'stages':[]}
    def stage(name):
        now=time.perf_counter()-started
        if run['stages'] and run['stages'][-1]['status']=='RUNNING':
            previous=run['stages'][-1]; previous.update(status='COMPLETE',seconds=now-previous['started_seconds'])
        run['stages'].append({'name':name,'status':'RUNNING','started_seconds':now})
        atomic_json(temp/'metadata/run.json',run)
    try:
        stage('topology')
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
        stage('geometry')
        t=time.perf_counter(); visual,_,_=field.mesh(spec['mesh']['visual_voxel']); collision,grid,origin=field.mesh(spec['mesh']['collision_voxel']); timings['geometry_seconds']=time.perf_counter()-t
        stage('validation')
        t=time.perf_counter(); validation,clearances=validate(spec,routes,graph,field,visual,collision,grid,origin); timings['validation_seconds']=time.perf_counter()-t
        dump(temp/'metadata/validation.json',validation)
        dump(temp/'navigation/clearance.json',{'visual':clearances['visual'].tolist(),'collision':clearances['collision'].tolist(),'ordering':'routes concatenated in centerline.json order'})
        stage('metrics')
        t=time.perf_counter(); metrics,visibility=compute_metrics(spec,routes,graph,collision,clearances['collision']); timings['metrics_seconds']=time.perf_counter()-t
        metrics.update({'visual_triangles':len(visual.faces),'collision_triangles':len(collision.faces),'validation':validation['status']})
        dump(temp/'navigation/visibility_horizon.json',visibility)
        stage('material_and_export')
        write_material(spec['material'],temp/'materials')
        write_obj(visual,temp/'visual/cave_visual.obj',visual=True); write_obj(collision,temp/'collision/cave_collision.obj')
        for name,mesh in [('visual',visual),('collision',collision)]: np.savez_compressed(temp/name/'mesh.npz',vertices=mesh.vertices,faces=mesh.faces)
        stage('topology_preview')
        topology_preview(routes,graph,visibility,temp/'previews',spec['name'])
        geometry_spec={k:v for k,v in spec.items() if k not in ['name','description','material','split','ood_factors']}
        provenance={'composer_version':'0.2.0','seed':int(seed),'geometry_config_sha256':digest(geometry_spec),
                    'visual_mesh_sha256':mesh_digest(visual),'collision_mesh_sha256':mesh_digest(collision),
                    'appearance_sha256':digest(spec['material']),'platform':platform.platform(),'python':platform.python_version(),
                    'dependencies':{p:importlib.metadata.version(p) for p in ['numpy','scipy','scikit-image','trimesh','PyYAML']},
                    'geometry_source':'independent procedural level set; no scanned geometry',
                    'coordinates':'metres, right handed, Z up; cave boundary normals point into void',
                    'water_baked':False,'split':spec['split'],'generation':timings}
        provenance['source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob('*.py'))}
        provenance['environment']=environment
        timings['bundle_seconds_before_render']=time.perf_counter()-started
        if render and validation['status']=='VALID':
            stage('blender_render')
            script=Path(__file__).resolve().parent/'blender_render.py'
            command=[str(executable),'--background','--python-exit-code','1','--python',str(script),'--','--scene',str(temp)]
            if save_blend: command.append('--save-blend')
            t=time.perf_counter()
            with (temp/'metadata/render.log').open('w',encoding='utf-8') as log:
                subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
            if not (temp/'previews/render_info.json').exists(): raise RuntimeError('Blender exited without completing all previews')
            stage('intersection_audit')
            audit_command=[str(executable),'--background','--python-exit-code','1','--python',str(Path(__file__).parent/'blender_audit.py'),'--','--scene',str(temp)]
            with (temp/'metadata/intersection_audit.log').open('w',encoding='utf-8') as log:
                subprocess.run(audit_command,stdout=log,stderr=subprocess.STDOUT,check=True)
            audit=json.loads((temp/'metadata/intersection_audit.json').read_text())
            attach_intersection_audit(validation,audit)
            metrics['validation']=validation['status']
            dump(temp/'metadata/validation.json',validation)
            timings['render_seconds']=time.perf_counter()-t
        stage('finalize')
        timings['total_seconds']=time.perf_counter()-started
        metrics['generation_seconds']=timings['total_seconds']
        dump(temp/'metadata/metrics.json',metrics); dump(temp/'metadata/provenance.json',provenance)
        run['stages'][-1].update(status='COMPLETE',seconds=time.perf_counter()-started-run['stages'][-1]['started_seconds'])
        run.update(status='COMPLETE' if validation['status']=='VALID' else 'INVALID',finished_utc=datetime.now(timezone.utc).isoformat(),total_seconds=time.perf_counter()-started)
        atomic_json(temp/'metadata/run.json',run)
        manifest=bundle_checksums(temp)
        dump(temp/'metadata/checksums.json',manifest)
        temp.rename(target)
        if validation['status']!='VALID': raise ValueError(f"Scene INVALID; retained diagnostics at {target}: {[k for k,v in validation['checks'].items() if not v]}")
        return {'path':str(target),'status':validation['status'],'metrics':metrics}
    except BaseException as exc:
        if temp.exists():
            run['status']='INTERRUPTED' if isinstance(exc,(KeyboardInterrupt,SystemExit)) else 'ERROR'
            run['error']={'type':type(exc).__name__,'message':str(exc)}
            if run['stages']:
                run['stages'][-1].update(status=run['status'],seconds=time.perf_counter()-started-run['stages'][-1]['started_seconds'])
            atomic_json(temp/'metadata/run.json',run)
            dump(temp/'metadata/failure.json',{'error':type(exc).__name__,'message':str(exc),'stage':run['stages'][-1]['name'] if run['stages'] else 'initialization'})
            failed=target.with_name(target.name+'.failed')
            if not failed.exists(): temp.rename(failed)
        raise
