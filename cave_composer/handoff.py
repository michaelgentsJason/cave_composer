"""Offline, immutable task delivery and strict collaborator-result intake.

No simulator or learner is launched. A checked adapter is not runtime evidence.
"""
import json,math,shutil
from pathlib import Path
from .bundle import file_sha256
from .tasks import load_task_pack

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write_new(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(data,stream,indent=2,allow_nan=False);stream.write('\n')

def contained(root,relative):
    root=Path(root).resolve();path=(root/relative).resolve()
    if not path.is_relative_to(root) or Path(relative).is_absolute():raise ValueError('Nonportable or escaping path')
    return path

def create_handoff(packs,profile,output,dataset_id):
    """Copy verified source packs to a NEW hash-locked snapshot, retaining splits."""
    output=Path(output).resolve();profile=read(profile)
    if output.exists():raise FileExistsError('Frozen handoff cannot be overwritten')
    sources=[Path(p).resolve() for p in packs]
    if not sources or not isinstance(dataset_id,str) or not dataset_id.strip():raise ValueError('Nonempty source list and dataset ID required')
    if any(p==output or p in output.parents or output in p.parents for p in sources):raise ValueError('Separate output required')
    checked=[load_task_pack(p) for p in sources]
    output.mkdir(parents=True);scenes=[];episodes=[];groups={}
    for i,(source,(contract,accepted)) in enumerate(zip(sources,checked)):
        m=read(source/'metadata/manifest.json');group='generated:'+m['source_mesh_files']['collision']
        split=m['source_split']
        if group in groups and groups[group]!=split:raise ValueError('Same geometry across splits')
        groups[group]=split
        scene_id=f'scene_{i:04d}';dest=output/'assets'/scene_id
        shutil.copytree(source,dest)
        # Recheck the copied snapshot rather than trusting a successful copy.
        load_task_pack(dest)
        scenes.append({'scene_id':scene_id,'source_name':m['source_name'],'source_group':group,
            'split':split,'task_pack':dest.relative_to(output).as_posix(),
            'generator_identity':{'source_code_hashes':m['environment']['source_sha256'],
                                  'source_checksums_sha256':m['source_checksums_sha256'],
                                  'source_mesh_files':m['source_mesh_files']},
            'units':'metres','coordinate_transform':[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],
            'surface':'closed_reference','robot_envelope':contract['robot_envelope'],
            'visual':f'assets/{scene_id}/'+contract['visual'],'collision':f'assets/{scene_id}/'+contract['collision'],
            'post_export_validation':'inherited closed reference certificate only; simulator conversion not checked'})
        for task in accepted:
            episodes.append({'episode_id':scene_id+'/'+task['id'],'scene_id':scene_id,'task_id':task['id'],
                'source_group':group,'split':split,'task_kind':'interior_pair_not_full_exit',
                'reset':task['start'],'goal':task['goal'],'budget':profile['task_budget']})
    write_new(output/'platform_profile.json',profile)
    write_new(output/'episodes.json',{'episodes':episodes,'scope':'interface-review list, not an approved final evaluation schedule'})
    manifest={'schema_version':1,'dataset_id':dataset_id,'purpose':'interface_review_not_training_release',
        'frozen':True,'status':'adapter_checked','scenes':scenes,'episodes':'episodes.json',
        'profile':'platform_profile.json','simulator_runtime_verified':False,'approved_for_training':False,
        'multi_scene_sampling':profile['training'],'files':{}}
    manifest['files']={p.relative_to(output).as_posix():file_sha256(p) for p in sorted(output.rglob('*')) if p.is_file()}
    write_new(output/'manifest.json',manifest)
    write_new(output/'manifest_digest.json',{'sha256':file_sha256(output/'manifest.json')})
    return preflight(output)

def preflight(folder,require_runtime=False):
    folder=Path(folder);m=read(folder/'manifest.json')
    if file_sha256(folder/'manifest.json')!=read(folder/'manifest_digest.json')['sha256']:raise ValueError('Manifest changed')
    actual={p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
    expected=set(m['files'])|{'manifest.json','manifest_digest.json'}
    if actual!=expected:raise ValueError('Frozen inventory changed')
    for name,digest in m['files'].items():
        if file_sha256(contained(folder,name))!=digest:raise ValueError('Asset hash mismatch: '+name)
    ids=set();groups={};expected_episodes={}
    for scene in m['scenes']:
        if scene['scene_id'] in ids:raise ValueError('Duplicate scene id')
        ids.add(scene['scene_id']);group=scene['source_group']
        if group in groups and groups[group]!=scene['split']:raise ValueError('Source split overlap')
        groups[group]=scene['split']
        _,accepted=load_task_pack(contained(folder,scene['task_pack']))
        for task in accepted:
            expected_episodes[scene['scene_id']+'/'+task['id']] = {
                'scene_id':scene['scene_id'],'task_id':task['id'],'source_group':group,
                'split':scene['split'],'reset':task['start'],'goal':task['goal'],
                'task_kind':'interior_pair_not_full_exit'}
    episodes=read(contained(folder,m['episodes']))['episodes']
    if len({e['episode_id'] for e in episodes})!=len(episodes):raise ValueError('Duplicate episode id')
    if {e['episode_id'] for e in episodes}!=set(expected_episodes):raise ValueError('Delivery differs from accepted task inventory')
    for episode in episodes:
        expected=expected_episodes[episode['episode_id']]
        if any(episode.get(k)!=v for k,v in expected.items()):raise ValueError('Delivery reset/goal or identity differs from validated task')
    profile=read(contained(folder,m['profile']))
    blockers=['collaborator_runtime_receipt_missing','active_training_manifest_unconfirmed']
    if 'UNCONFIRMED' in json.dumps(profile):blockers.append('platform_profile_unconfirmed')
    if any(e['task_kind']!='full_exit' for e in episodes):blockers.append('review_tasks_are_not_full_exit_benchmark')
    if require_runtime:raise ValueError('Not simulator-runtime verified: '+','.join(blockers))
    return {'status':'adapter_checked','scenes':len(ids),'distinct_geometry_groups':len(groups),'episodes':len(episodes),'all_file_hashes_checked':True,
            'simulator_runtime_verified':False,'training_ready':False,'blockers':blockers}

def validate_results(rows,run,episodes,root):
    """Validate complete fixed-episode receipts, not inferred policy performance."""
    if run.get('template_only') is True:raise ValueError('Fill and explicitly finalize the run template')
    def digest(value):
        return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)
    for key in ['checkpoint_sha256','dataset_manifest_sha256','config_sha256','normalizer_sha256','preprocessing_sha256','episode_manifest_sha256']:
        if not digest(run.get(key)):raise ValueError('Missing hash: '+key)
    if run.get('algorithm') not in ['FlashSAC','recurrent_visual_PPO']:raise ValueError('Unknown baseline')
    if not run.get('dataset_id') or not run.get('inference_rule'):raise ValueError('Run identity incomplete')
    if type(run.get('training_seed')) is not int or run['training_seed']<0:raise ValueError('Invalid seed')
    if run.get('policy_frozen') is not True or type(run.get('in_episode_interventions')) is not int or run['in_episode_interventions']!=0:raise ValueError('Frozen, intervention-free evaluation required')
    if run.get('episodes_fixed_before_policy_evaluation') is not True:raise ValueError('Episode preselection declaration required')
    if not episodes or len({e['episode_id'] for e in episodes})!=len(episodes):raise ValueError('Empty or duplicate fixed episode list')
    expected={e['episode_id']:e for e in episodes};seen=set()
    for row in rows:
        key=row.get('episode_id')
        if key in seen or key not in expected:raise ValueError('Duplicate or unknown episode')
        seen.add(key)
        if row.get('checkpoint_sha256')!=run['checkpoint_sha256']:raise ValueError('Checkpoint switch')
        if row.get('dataset_id')!=run['dataset_id']:raise ValueError('Dataset version mismatch')
        if row.get('scene_id')!=expected[key]['scene_id']:raise ValueError('Scene mismatch')
        outcome=row.get('outcome')
        if outcome not in ['success','collision','out_of_bounds','timeout','not_run']:raise ValueError('Unknown outcome')
        if outcome=='not_run' and (row.get('elapsed_seconds') is not None or not row.get('not_run_reason')):raise ValueError('Unexecuted episode must have null elapsed time and a reason')
        for flag in ['success','collision','out_of_bounds','timeout']:
            if type(row.get(flag)) is not bool or row[flag]!=(outcome==flag):raise ValueError('Contradictory outcome flags')
        for key in ['elapsed_seconds','remaining_traversable_distance_m']:
            val=row.get(key)
            if val is None and (outcome=='not_run' or key=='remaining_traversable_distance_m'):
                if not row.get(key+'_reason'):raise ValueError('Missing-value reason required')
                continue
            if type(val) not in [int,float] or not math.isfinite(val) or val<0:raise ValueError('Invalid metric: '+key)
        if outcome!='not_run':
            if not digest(row.get('trajectory_sha256')):raise ValueError('Trajectory hash missing')
            path=contained(root,row['trajectory'])
            if not path.is_file() or file_sha256(path)!=row['trajectory_sha256']:raise ValueError('Trajectory bytes mismatch')
        if not row.get('remaining_distance_method'):raise ValueError('Distance definition missing')
    if seen!=set(expected):raise ValueError('Missing episodes; retain not_run records instead of dropping them')
    return {'status':'adapter_checked','records':len(rows),'executed':sum(r['outcome']!='not_run' for r in rows),
        'scope':'log schema/integrity only; simulator provenance and trajectories still require review',
        'policy_evaluated':False}
