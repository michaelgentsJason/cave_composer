"""Disjoint seed namespaces and explicit factor supports, including composition OOD."""
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
import json
import shutil
import time
import uuid
from datetime import datetime,timezone
import numpy as np
import yaml
from .spec import load_spec,merge
from .pipeline import generate,digest
from .bundle import atomic_json,dataset_lock,environment_signature,file_sha256,verify_bundle

SPLITS={'train':11,'validation':23,'id_test':37,'ood_geometry':51,'ood_composition':67,'ood_topology':83}


def scene_seed(split,seed,index=0):
    if split not in SPLITS: raise ValueError(f'Unknown split: {split}')
    for name,value in [('seed',seed),('index',index)]:
        if isinstance(value,(bool,np.bool_)) or not isinstance(value,(int,np.integer)) or value<0:
            raise ValueError(f'{name} must be a nonnegative integer')
    # Namespace is carried in low bits, making split seed sets disjoint rather
    # than merely relying on a statistically unlikely random collision.
    return (int(seed)+int(index))*128+SPLITS[split]


def sample_config(split='train',difficulty='medium',seed=42,sampler='legacy_v02',family='mixed'):
    split=split.lower()
    if sampler == 'topology_v03':
        from .sampling import sample_topology_config
        return sample_topology_config(split,difficulty,scene_seed(split,seed),family)
    if sampler != 'legacy_v02' or family != 'mixed' or split == 'ood_topology':
        raise ValueError('Use topology_v03 for named families and topology OOD')
    if difficulty not in ('easy','medium','hard'): raise ValueError('difficulty must be easy, medium or hard')
    rng=np.random.default_rng(scene_seed(split,seed))
    factors=rng.integers(0,2,3).astype(bool) # sharp, narrow, descending
    if split=='ood_composition': factors[:]=True
    elif split!='ood_geometry' and factors.all(): factors[int(rng.integers(0,3))]=False
    if difficulty=='easy' and split not in ('ood_composition','ood_geometry'): factors[:]=False
    sharp,narrow,descending=map(bool,factors)
    angle=float(rng.uniform(60,90) if sharp else rng.uniform(20,55))
    width=float(rng.uniform(3.0,3.6) if narrow else rng.uniform(4.3,6))
    slope=float(rng.uniform(-18,-10) if descending else rng.uniform(-4,4))
    if split=='ood_geometry':
        angle=float(rng.uniform(120,165)); width=float(rng.uniform(2.7,2.95)); slope=float(rng.uniform(-28,-22))
    route=[{'straight':float(rng.uniform(10,17))}, {'turn':angle,'radius':float(rng.uniform(4.5,7))},
           {'straight':float(rng.uniform(10,16)),'slope':slope}, {'turn':-angle*0.8,'radius':5.5},
           {'straight':float(rng.uniform(12,19))}]
    raw={'name':f'{split}_{seed:06d}','split':split,'description':f'{difficulty} sampled scene',
         'corridor':{'width':width,'height':float(rng.uniform(3.4,4.7)),'section':str(rng.choice(['irregular','asymmetric','flattened','fracture']))},
         'route':route,'material':{'style':str(rng.choice(['limestone','sandstone','basalt'])),'seed':int(rng.integers(0,2**31))},
         'geology':{'amplitude':float(rng.uniform(0.25,0.43)),'formations':int(rng.integers(5,15))},
         'ood_factors':{'sharp':bool(angle>=60),'narrow':bool(width<=3.6),'descending':bool(slope<=-10)}}
    if split!='ood_geometry' and difficulty!='easy' and rng.random()<0.35:
        raw['branches']=[{'at':0.20,'heading':-90,'route':[{'straight':float(rng.uniform(8,14))}]}]
    if rng.random()<0.3: raw['chambers']=[{'at':0.55,'radii':[5,4.5,3.8],'lobes':4}]
    return load_spec(raw)


def _failure_details(path):
    for folder in [path,path.with_name(path.name+'.failed')]:
        if not folder.is_dir():
            continue
        result={}
        run_path=folder/'metadata/run.json'
        if run_path.exists():
            run=json.loads(run_path.read_text(encoding='utf-8'))
            result['failed_stage']=run['stages'][-1]['name'] if run.get('stages') else 'initialization'
            result['run_status']=run['status']
        validation_path=folder/'metadata/validation.json'
        if validation_path.exists():
            validation=json.loads(validation_path.read_text(encoding='utf-8'))
            result['failed_checks']=[name for name,passed in validation['checks'].items() if not passed]
            if result['failed_checks']:
                result['failed_stage']='intersection_audit' if result['failed_checks']==['bvh_no_nonadjacent_intersections'] else 'validation'
        metrics_path=folder/'metadata/metrics.json'
        if metrics_path.exists():
            result['metrics']=json.loads(metrics_path.read_text(encoding='utf-8'))
        result['diagnostics']=folder.name
        return result
    return {}


def _job(payload):
    config,seed,path,render,blender,save_blend,expected_environment=payload
    try:
        result=generate(config,seed,path,render=render,blender=blender,save_blend=save_blend)
        run=verify_bundle(path)
        if run['environment_sha256']!=expected_environment:
            raise RuntimeError('Generator source/dependencies changed while this dataset was running')
        return {'status':'VALID','metrics':result['metrics']}
    except Exception as exc:
        details=_failure_details(path)
        return {'status':'INVALID' if details.get('failed_checks') else 'ERROR',
                'error':f'{type(exc).__name__}: {exc}',**details}


def _distribution(value):
    d=yaml.safe_load(Path(value).read_text(encoding='utf-8')) if isinstance(value,(str,Path)) else value
    if not isinstance(d,dict): raise ValueError('Distribution must be a mapping')
    unknown=set(d)-{'schema_version','split','difficulty','base_seed','overrides','sampler','family'}
    if unknown: raise ValueError(f'Unknown distribution keys: {sorted(unknown)}')
    if d.get('schema_version',1)!=1 or isinstance(d.get('schema_version'),bool):
        raise ValueError('Only distribution schema_version 1 is supported')
    split=str(d.get('split','train')).lower()
    base=d.get('base_seed',42)
    scene_seed(split,base)
    overrides=d.get('overrides',{})
    if not isinstance(overrides,dict) or set(overrides)-{'mesh','material'}:
        raise ValueError('Distribution overrides are limited to mesh/material; geometry changes require a new named distribution')
    sampler=d.get('sampler','legacy_v02'); family=d.get('family','mixed')
    if sampler not in ('legacy_v02','topology_v03'):
        raise ValueError('Unknown sampler')
    return {'schema_version':1,'split':split,'difficulty':d.get('difficulty','medium'),
            'base_seed':int(base),'overrides':overrides,'sampler':sampler,'family':family}


def _existing_artifacts(root,name):
    candidates=[root/name,root/(name+'.failed'),*sorted(root.glob('.'+name+'.building-*'))]
    return [p for p in candidates if p.exists()]


def _check_identity(path,config_sha,seed,environment_sha):
    journal=path/'metadata/run.json'
    if not journal.is_file():
        return None
    run=json.loads(journal.read_text(encoding='utf-8'))
    expected=(config_sha,seed,environment_sha)
    if (run['config_sha256'],run['seed'],run['environment_sha256'])!=expected:
        raise ValueError(f'Existing scene has a different config, seed or generator: {path}')
    return run


def _archive(root,name,record,config_sha,seed,environment_sha):
    artifacts=_existing_artifacts(root,name)
    if not artifacts:
        return
    for path in artifacts:
        if path.is_symlink() or not path.resolve().is_relative_to(root) or not (path/'.cave_composer_bundle').is_file():
            raise ValueError(f'Refusing to archive an unowned artifact: {path}')
        _check_identity(path,config_sha,seed,environment_sha)
    archive=root/'.attempts'/name/f"attempt_{record['attempts']:03d}_{uuid.uuid4().hex[:8]}"
    if not archive.resolve().is_relative_to(root):
        raise ValueError('Archive path escaped dataset')
    archive.mkdir(parents=True)
    for path in artifacts:
        destination=archive/path.name
        path.rename(destination)
        record.setdefault('history',[]).append(destination.relative_to(root).as_posix())


def generate_dataset(distribution,num_scenes=100,workers=1,output='outputs/dataset',
                     render=False,blender=None,save_blend=False,resume=False,retry_failed=False):
    """Incremental scene-level restart: verify successes, preserve failures, keep seeds."""
    for name,value in [('num_scenes',num_scenes),('workers',workers)]:
        if isinstance(value,bool) or not isinstance(value,int) or value<1:
            raise ValueError(f'{name} must be a positive integer')
    if retry_failed and not resume: raise ValueError('retry_failed requires resume=True')
    if save_blend and not render: raise ValueError('save_blend requires render=True')
    d=_distribution(distribution)
    renderer=None
    if render:
        import os
        executable=blender or os.environ.get('BLENDER_PATH') or 'blender'
        blender=shutil.which(str(executable))
        if not blender: raise ValueError('Blender not found; pass --blender or set BLENDER_PATH')
        renderer={'executable':str(Path(blender).resolve()),'sha256':file_sha256(blender)}
    environment=environment_signature()
    environment_sha=digest(environment)
    contract={'distribution':d,'environment':environment,'render':bool(render),'save_blend':bool(save_blend),'renderer':renderer}
    fingerprint=digest(contract)
    configs=[load_spec(merge(sample_config(d['split'],d['difficulty'],d['base_seed']+i,
                  **({'sampler':d['sampler'],'family':d['family']} if d['sampler']!='legacy_v02' or d['family']!='mixed' else {})),
                  d['overrides'])) for i in range(num_scenes)]
    root=Path(output).resolve()
    manifest_path=root/'manifest.json'
    if root.exists():
        if not resume: raise FileExistsError(f'Refusing to overwrite dataset: {root}; use --resume')
        if not (root/'.cave_composer_dataset').is_file() or not manifest_path.is_file():
            raise ValueError('Resume requires a dataset created by the incremental pipeline (manifest schema 2)')
    else:
        if resume: raise FileNotFoundError(f'No dataset to resume: {root}')
        root.mkdir(parents=True)
        (root/'.cave_composer_dataset').write_text('2\n',encoding='utf-8')
    started=time.perf_counter()
    with dataset_lock(root):
        if resume:
            manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
            if manifest.get('schema_version')!=2 or manifest.get('contract_sha256')!=fingerprint:
                raise ValueError('Resume contract mismatch: distribution, source, dependencies or render settings changed; use a new output directory')
            if num_scenes<manifest['requested']:
                raise ValueError('Cannot shrink a dataset during resume; retain or increase num_scenes')
        else:
            manifest={'schema_version':2,'distribution':d,'contract':contract,'contract_sha256':fingerprint,
                      'records':[],'runs':[],'requested':num_scenes,
                      'retry_policy':'Explicit same-seed retry only; previous attempts are archived, never substituted',
                      'realistic_ood':'external untouched scans; not generated or included'}
        old_count=len(manifest['records'])
        for i in range(old_count,num_scenes):
            manifest['records'].append({'index':i,'seed':scene_seed(d['split'],d['base_seed'],i),
                'config_sha256':digest(configs[i]),'path':f'scene_{i:06d}','status':'PENDING','attempts':0})
        manifest.update(requested=num_scenes,workers=workers,status='RUNNING')
        scheduled=[]
        reused=0
        for record,config in zip(manifest['records'],configs):
            expected_name=f"scene_{record['index']:06d}"
            expected_seed=scene_seed(d['split'],d['base_seed'],record['index'])
            if record['path']!=expected_name or record['seed']!=expected_seed or record['config_sha256']!=digest(config):
                raise ValueError('Manifest scene identity mismatch')
            folder=root/expected_name
            run=_check_identity(folder,record['config_sha256'],record['seed'],environment_sha) if folder.exists() else None
            if record['status']=='VALID' or (run and run['status']=='COMPLETE'):
                verify_bundle(folder)
                if run is None: raise ValueError(f'Missing scene journal: {folder}')
                record.update(status='VALID',metrics=json.loads((folder/'metadata/metrics.json').read_text(encoding='utf-8')))
                reused+=1
                continue
            # A completed error may have reached disk just before the process was interrupted.
            details=_failure_details(folder)
            if details.get('run_status') in ('ERROR','INVALID'):
                record.update(status='INVALID' if details.get('failed_checks') else 'ERROR',**details)
            if record['status'] in ('INVALID','ERROR') and not retry_failed:
                continue
            _archive(root,expected_name,record,record['config_sha256'],record['seed'],environment_sha)
            for key in ['error','failed_stage','failed_checks','run_status','diagnostics','metrics']:
                record.pop(key,None)
            record.update(status='RUNNING',attempts=record['attempts']+1)
            scheduled.append((record,(config,record['seed'],folder,render,blender,save_blend,environment_sha)))
        run_record={'started_utc':datetime.now(timezone.utc).isoformat(),'workers':workers,
                    'resume':bool(resume),'retry_failed':bool(retry_failed),'reused':reused,'scheduled':len(scheduled),'completed':0}
        manifest['runs'].append(run_record)

        def persist():
            records=manifest['records']
            manifest['valid']=sum(r['status']=='VALID' for r in records)
            manifest['invalid']=sum(r['status'] in ('INVALID','ERROR') for r in records)
            manifest['errors']=sum(r['status']=='ERROR' for r in records)
            manifest['pending']=sum(r['status'] in ('PENDING','RUNNING') for r in records)
            atomic_json(manifest_path,manifest)

        def accept(record,result):
            record.update(result)
            run_record['completed']+=1
            persist()
            print(json.dumps({'index':record['index'],'seed':record['seed'],'status':record['status'],
                              'finished':manifest['valid']+manifest['invalid'],'requested':num_scenes}),flush=True)

        persist()
        try:
            if workers==1:
                for record,payload in scheduled:
                    accept(record,_job(payload))
            elif scheduled:
                with ProcessPoolExecutor(max_workers=workers) as pool:
                    futures={pool.submit(_job,payload):record for record,payload in scheduled}
                    for future in as_completed(futures):
                        try:
                            result=future.result()
                        except Exception as exc:
                            result={'status':'ERROR','error':f'{type(exc).__name__}: {exc}','failed_stage':'worker_process'}
                        accept(futures[future],result)
            manifest['status']='COMPLETE'
        except BaseException:
            manifest['status']='INTERRUPTED'
            raise
        finally:
            run_record.update(finished_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.perf_counter()-started)
            persist()
            from .quality import write_dataset_report
            write_dataset_report(root,manifest)
        return manifest
