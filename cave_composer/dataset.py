"""Disjoint seed namespaces and explicit factor supports, including composition OOD."""
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
import json
import numpy as np
import yaml
from .spec import load_spec,merge
from .pipeline import generate,dump

SPLITS={'train':11,'validation':23,'id_test':37,'ood_geometry':51,'ood_composition':67}


def scene_seed(split,seed,index=0):
    if split not in SPLITS: raise ValueError(f'Unknown split: {split}')
    # Namespace is carried in low bits, making split seed sets disjoint rather
    # than merely relying on a statistically unlikely random collision.
    return (int(seed)+int(index))*128+SPLITS[split]


def sample_config(split='train',difficulty='medium',seed=42):
    split=split.lower()
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


def _job(payload):
    index,config,seed,path,render,blender=payload
    try:
        result=generate(config,seed,path,render=render,blender=blender)
        return {'index':index,'seed':seed,'status':'VALID','path':str(path),'metrics':result['metrics']}
    except Exception as exc:
        return {'index':index,'seed':seed,'status':'INVALID','path':str(path),'error':f'{type(exc).__name__}: {exc}'}


def generate_dataset(distribution,num_scenes=100,workers=1,output='outputs/dataset',render=False,blender=None):
    d=yaml.safe_load(Path(distribution).read_text()) if isinstance(distribution,(str,Path)) else distribution
    unknown=set(d)-{'schema_version','split','difficulty','base_seed','overrides'}
    if unknown: raise ValueError(f'Unknown distribution keys: {unknown}')
    if num_scenes<1 or workers<1: raise ValueError('num_scenes and workers must be positive')
    root=Path(output).resolve()
    if root.exists(): raise FileExistsError(f'Refusing to overwrite dataset: {root}')
    root.mkdir(parents=True)
    split=d.get('split','train').lower(); base=int(d.get('base_seed',42))
    payload=[]
    for i in range(num_scenes):
        config=sample_config(split,d.get('difficulty','medium'),base+i)
        # Only numerical/render cost overrides: geometry-factor edits could silently
        # invalidate the advertised held-out support.
        overrides=d.get('overrides',{})
        if set(overrides)-{'mesh','material'}: raise ValueError('Distribution overrides are limited to mesh/material; use a new named distribution for geometry changes')
        config=load_spec(merge(config,overrides))
        payload.append((i,config,scene_seed(split,base,i),root/f'scene_{i:06d}',render,blender))
    records=[]
    if workers==1:
        for item in payload:
            record=_job(item); records.append(record); print(json.dumps({'index':record['index'],'status':record['status']}),flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures=[pool.submit(_job,item) for item in payload]
            for future in as_completed(futures):
                record=future.result(); records.append(record); print(json.dumps({'index':record['index'],'status':record['status']}),flush=True)
    records.sort(key=lambda r:r['index'])
    manifest={'schema_version':1,'distribution':d,'requested':num_scenes,'valid':sum(r['status']=='VALID' for r in records),
              'invalid':sum(r['status']!='VALID' for r in records),'workers':workers,'records':records,
              'retry_policy':'no silent replacement or seed changes; all failures retained',
              'realistic_ood':'external untouched scans; not generated or included'}
    dump(root/'manifest.json',manifest)
    return manifest
