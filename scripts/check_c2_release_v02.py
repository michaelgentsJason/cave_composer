"""Read-only delivery integrity, group isolation, reset binding and mesh checks."""
from pathlib import Path
import json,sys,argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cave_composer.delivery_validation import sha256
from cave_composer.tasks import load_task_pack
from cave_composer.bundle import verify_portal_export
def check(root):
    root=root.resolve();m=json.loads((root/'manifest.json').read_text())
    if sha256(root/'manifest.json')!=json.loads((root/'manifest_digest.json').read_text())['sha256']:raise ValueError('Manifest changed')
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if actual!=set(m['files'])|{'manifest.json','manifest_digest.json'}:raise ValueError('Inventory changed')
    for rel,digest in m['files'].items():
        p=(root/rel).resolve()
        if not p.is_relative_to(root) or sha256(p)!=digest:raise ValueError('Hash/path failure '+rel)
    groups={};expected={}
    for s in m['scenes']:
        if s['base_group'] in groups and groups[s['base_group']]!=s['split']:raise ValueError('Base group crosses splits')
        groups[s['base_group']]=s['split'];_,tasks=load_task_pack(root/s['closed_tasks']);verify_portal_export(root/s['open_bundle'])
        for t in tasks:expected[s['scene_id']+'/'+t['id']]=(t['start'],t['goal'])
        p=json.loads((root/s['open_bundle']/'navigation/portal_path.json').read_text())
        expected[s['scene_id']+'/full_exit_0000']=(p['start'],p['goal'])
    eps=json.loads((root/'episodes.json').read_text())['episodes']
    if len(eps)!=len(expected) or {e['episode_id'] for e in eps}!=set(expected):raise ValueError('Episode inventory differs')
    for e in eps:
        start,goal=expected[e['episode_id']]
        if e['task_kind']=='interior_pair':valid=e['reset']==start and e['goal']==goal
        else:valid=e['reset']['position_m']==start and e['goal']['position_m']==goal
        if not valid:raise ValueError('Reset/goal binding changed')
    return {'status':'PASS','scenes':len(m['scenes']),'fixed_episodes':len(eps),'primary_episodes':sum(e['primary_matched_schedule'] for e in eps),
            'manifest_sha256':sha256(root/'manifest.json'),'training_approved':False,'simulator_lab_vehicle_runtime_pending':True}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--release',type=Path,required=True);a=p.parse_args();print(json.dumps(check(a.release),indent=2))
