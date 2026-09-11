"""Six preregistered cave requests x three arms; no outcome-based retries."""
from pathlib import Path
import argparse, copy, datetime, hashlib, json, subprocess, sys, time, traceback
import numpy as np
import trimesh
from matplotlib.path import Path as PolygonPath
from scipy.spatial import ConvexHull
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cave_composer.pipeline import generate
from cave_composer.spec import load_spec
from cave_composer.routes import build_routes
from cave_composer.delivery_validation import verify_delivered_task, sha256


def write(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def initialize(root):
    if (root/'preregistration.json').exists(): raise FileExistsError('Already preregistered')
    root.mkdir(parents=True,exist_ok=True)
    specs=[]
    for i in range(6):
        stress=i>=4
        spec={'name':f'c1_request_{i:02d}', 'split':['train','train','development','generated_id_test','stress','stress'][i],
          'corridor':{'width':[5.2,5.8,5.2,5.2,2.8,2.8][i],'height':[4.3,4.8,4.3,4.3,2.8,2.8][i],
                      'variation':.15,'section':'irregular'},
          'geology':{'amplitude':.75 if stress else .3,'strata':.22 if stress else .12,'formations':22 if stress else 6},
          'mesh':{'visual_voxel':.24,'collision_voxel':.32,'max_voxels':4000000},
          'robot':{'radius':.35,'margin':.2},
          'material':{'style':'limestone','seed':88001,'roughness':.85},
          'route':[{'straight':8},{'turn':50 if i!=2 else -65,'radius':6},{'straight':10}],
          'branches':[], 'chambers':[], 'bottlenecks':[],
          'morphology':{'cross_section':{'amplitude':.18,'eccentricity':.12,'length_scale':7},
                        'roughness':{'contrast':.5,'length_scale':6},'features':[]}}
        if i==1: spec['branches']=[{'at':.43,'heading':100,'route':[{'straight':9}]}]
        if i==2:
            spec['chambers']=[{'at':.6,'radii':[4,3.4,3],'lobes':4}]
            spec['route'][2]['slope']=12
        if stress:
            spec['morphology']['features']=[{'id':'intrusion','kind':'ceiling_drop' if i==4 else 'wall_intrusion',
                                           'at':.55,'length':4,'span':4,'depth':2.2,'strength':1}]
        spec=load_spec(spec)
        specs.append(spec)
    requests=[]
    for i,spec in enumerate(specs):
        for arm in ['full','no_protection','restricted']:
            current=copy.deepcopy(spec)
            if arm=='restricted':
                current['branches']=[];current['chambers']=[];current.pop('morphology',None)
                current['corridor'].update(variation=0,section='oval')
                current['geology'].update(amplitude=0,strata=0,formations=0)
            filename=f'configs/request_{i:02d}_{arm}.json'
            write(root/filename,current)
            requests.append({'base_id':f'request_{i:02d}','arm':arm,'seed':88010+i,
                'stratum':'stress' if i>=4 else 'normal','split':spec['split'],
                'config':filename,'config_sha256':sha256(root/filename),
                'protect_passage':arm!='no_protection','scene':f'scenes/request_{i:02d}/{arm}'})
    prereg={'version':2,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'pilot_only','base_requests':6,'method_invocations':18,'requests':requests,
        'attempts_per_arm':1,'retries':0,'timeout_seconds_per_invocation':300,
        'max_astar_expansions':500000,'workers':1,'normal_base_requests':4,'stress_base_requests':2,
        'layout_screening':'Explicit layouts bypass random layout screening in all arms; no screening ablation claimed.',
        'acceptance':'Legacy generation gate AND independent task AND fresh checks of both delivered OBJ files.',
        'measurement':'17 fixed transverse sections on each delivered OBJ, smallest closed origin-containing contour; holes excluded; local contour proxy, not exact topology.',
        'metrics':['all requests/attempts, first/final yield','reasons and zero retries','independent witness length and clearance',
                   'requested and realized width/height, section nonconvexity/area CV','mesh-section centroid slope/turn proxy',
                   'requested vs accepted feature coverage','all stage costs, wall time including failures, seconds per accepted cave'],
        'unit_of_replication':'base cave; multiple arms paired; tasks are not independent caves',
        'no_expansion_rule':'No additional seeds or replacement of rejected caves. Infrastructure repair must retain original logs and be declared.',
        'figure_selection':['request_00','request_01','request_02','request_04'],
        'c2_rule':'Normal full/restricted requests only; 00/01 train,02 development,03 ID new-geometry test; same base group across arms.',
        'c2_tasks':{'requested_internal_tasks_per_scene':2,'task_seed':88200,'physical_exit_tasks_per_scene':1},
        'external_baseline':'Separate PLUME native and supported graph-input smoke; do not pool unmatched interfaces into paired yield.',
        'source_sha256':{p.relative_to(ROOT).as_posix():sha256(p) for p in [Path(__file__).resolve(),*sorted((ROOT/'cave_composer').glob('*.py'))]}}
    write(root/'preregistration.json',prereg)
    print('Preregistered 6 base requests, 18 method invocations',flush=True)


def measurements(folder):
    spec=json.loads((folder/'metadata/config.json').read_text())
    route=build_routes(spec)[0]
    result={'requested':{'width_m':spec['corridor']['width'],'height_m':spec['corridor']['height'],
              'route_length_m':float(route['s'][-1]),'branches':len(spec['branches']),'chambers':len(spec['chambers']),
              'morphology':spec.get('morphology',{}),'commands':spec['route']},'meshes':{}}
    for kind in ['visual','collision']:
        mesh=trimesh.load(folder/kind/f'cave_{kind}.obj',force='mesh',process=False)
        records=[]
        for fraction in np.linspace(.12,.88,17):
            i=round((len(route['points'])-1)*fraction);p=route['points'][i]
            t=route['points'][i+1]-route['points'][i-1];t/=np.linalg.norm(t)
            side=np.cross([0,0,1],t);side/=np.linalg.norm(side);up=np.cross(t,side)
            frame=np.column_stack([side,up]);section=mesh.section(plane_origin=p,plane_normal=t)
            choices=[]
            for curve in section.discrete if section is not None else []:
                if np.linalg.norm(curve[0]-curve[-1])>1e-5:continue
                xy=(curve-p)@frame
                if not PolygonPath(xy).contains_point((0,0)):continue
                a,b=xy[:-1],xy[1:];cross=a[:,0]*b[:,1]-b[:,0]*a[:,1];signed=cross.sum()/2
                if abs(signed)<1e-7:continue
                centroid=((a+b)*cross[:,None]).sum(0)/(6*signed)
                choices.append({'area_m2':float(abs(signed)),'width_m':float(np.ptp(xy[:,0])),
                    'height_m':float(np.ptp(xy[:,1])),'nonconvexity':float(1-abs(signed)/ConvexHull(a).volume),
                    'contour':xy.tolist(),'centroid_world':(p+frame@centroid).tolist()})
            record={'fraction':float(fraction),'s_m':float(route['s'][i]),'plane_origin':p.tolist(),
                    'plane_basis':frame.tolist(),'nominal_width_m':float(route['widths'][i]),'nominal_height_m':float(route['heights'][i])}
            record.update(min(choices,key=lambda c:c['area_m2']) if choices else {'invalid_section':'no_origin_enclosing_closed_contour'})
            records.append(record)
        valid=[r for r in records if 'area_m2' in r];summary={'valid_sections':len(valid),'requested_sections':len(records),
            'mesh_sha256':sha256(folder/kind/f'cave_{kind}.obj'),'triangles':len(mesh.faces),
            'aabb_extent_m':np.ptp(mesh.vertices,axis=0).tolist(),'watertight':bool(mesh.is_watertight)}
        if valid:
            for dim in ['width','height']:
                values=np.array([r[dim+'_m'] for r in valid]);nom=np.array([r['nominal_'+dim+'_m'] for r in valid])
                summary[dim+'_mean_m']=float(values.mean());summary[dim+'_mae_vs_nominal_m']=float(abs(values-nom).mean())
            areas=np.array([r['area_m2'] for r in valid])
            summary.update(area_cv=float(areas.std()/areas.mean()),mean_nonconvexity=float(np.mean([r['nonconvexity'] for r in valid])))
        if len(valid)==len(records):
            delta=np.diff([r['centroid_world'] for r in records],axis=0)
            summary['centroid_proxy_max_abs_slope_degrees']=float(np.degrees(np.arctan2(abs(delta[:,2]),np.linalg.norm(delta[:,:2],axis=1))).max())
            unit=delta/np.linalg.norm(delta,axis=1)[:,None]
            summary['centroid_proxy_total_turn_degrees']=float(np.degrees(np.arccos(np.clip(np.sum(unit[1:]*unit[:-1],axis=1),-1,1))).sum())
        result['meshes'][kind]={'sections':records,'summary':summary}
    return result


def worker(root,index):
    prereg=json.loads((root/'preregistration.json').read_text());request=prereg['requests'][index]
    cfg=root/request['config'];scene=root/request['scene'];out=root/'results'/f'{index:02d}.json'
    if out.exists():raise FileExistsError(out)
    if sha256(cfg)!=request['config_sha256']:raise ValueError('Preregistered configuration changed')
    record={'request':request,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'attempt':1,'retries':0}
    start=time.perf_counter()
    try:
        generate(cfg,request['seed'],scene,protect_passage=request['protect_passage'])
        record['generation_status']='VALID'
    except Exception as exc:
        record.update(generation_status='REJECTED_OR_ERROR',exception={'type':type(exc).__name__,'message':str(exc)})
        traceback.print_exc()
    record['generation_wall_seconds']=time.perf_counter()-start
    if not scene.exists():scene=scene.with_name(scene.name+'.failed')
    if (scene/'metadata/run.json').exists():record['run']=json.loads((scene/'metadata/run.json').read_text())
    if (scene/'metadata/validation.json').exists():
        v=json.loads((scene/'metadata/validation.json').read_text());record['failed_generation_checks']=[k for k,vv in v['checks'].items() if not vv]
    planning=scene/'navigation/planned_path.json'
    if planning.exists():
        record['planning']=json.loads(planning.read_text())
        if record['planning'].get('points'):
            t=time.perf_counter()
            record['delivered_check']=verify_delivered_task({k:scene/k/f'cave_{k}.obj' for k in ['visual','collision']},record['planning']['points'],.55)
            record['delivered_check_seconds']=time.perf_counter()-t
    if (scene/'visual/cave_visual.obj').exists():
        t=time.perf_counter()
        try:record['geometry']=measurements(scene)
        except Exception as exc:record['measurement_error']=repr(exc);traceback.print_exc()
        record['measurement_seconds']=time.perf_counter()-t
    record['accepted']=(record['generation_status']=='VALID' and record.get('planning',{}).get('status')=='PASS'
                        and record.get('delivered_check',{}).get('status')=='PASS')
    record['wall_seconds_including_measurement']=time.perf_counter()-start
    write(out,record)
    print(index,request['base_id'],request['arm'],'accepted',record['accepted'],'seconds',round(record['wall_seconds_including_measurement'],2),flush=True)


def run(root):
    prereg=json.loads((root/'preregistration.json').read_text())
    (root/'logs').mkdir(exist_ok=True)
    for i,request in enumerate(prereg['requests']):
        if (root/'results'/f'{i:02d}.json').exists():continue
        start=time.perf_counter()
        with (root/'logs'/f'{i:02d}.log').open('w',encoding='utf-8') as log:
            try:
                process=subprocess.run([sys.executable,__file__,'--root',str(root),'--worker',str(i)],stdout=log,stderr=subprocess.STDOUT,timeout=prereg['timeout_seconds_per_invocation'])
                error=None if process.returncode==0 else f'worker_exit_{process.returncode}'
            except subprocess.TimeoutExpired:error='worker_wall_time_budget_exhausted'
        if error and not (root/'results'/f'{i:02d}.json').exists():
            write(root/'results'/f'{i:02d}.json',{'request':request,'accepted':False,'attempt':1,'retries':0,
                'reason':error,'wall_seconds_including_measurement':time.perf_counter()-start})
        record=json.loads((root/'results'/f'{i:02d}.json').read_text())
        print(i,request['base_id'],request['arm'],record['accepted'],round(time.perf_counter()-start,1),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=ROOT/'outputs/c1_pilot_v02')
    parser.add_argument('--initialize',action='store_true');parser.add_argument('--worker',type=int)
    args=parser.parse_args()
    if args.initialize:initialize(args.root)
    elif args.worker is not None:worker(args.root,args.worker)
    else:run(args.root)
