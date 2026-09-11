"""Build a NEW handoff from preregistered normal cases; preserve old snapshots."""
from pathlib import Path
import argparse,sys,json,time,traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cave_composer.tasks import build_task_pack,load_task_pack
from cave_composer.portals import export_portals
from cave_composer.delivery_validation import verify_delivered_task,sha256
ROOT=Path('outputs/c2_pretraining_v02')
PILOT=Path('outputs/c1_pilot_v02')

def main():
    ROOT.mkdir(parents=True,exist_ok=False);records=[]
    prereg=json.loads((PILOT/'preregistration.json').read_text())
    for r in prereg['requests']:
        if r['stratum']!='normal' or r['arm']=='no_protection':continue
        sid=r['base_id']+'_'+r['arm'];source=PILOT/r['scene'];dest=ROOT/'task_packs'/sid;portal=ROOT/'open_assets'/sid
        record={'scene_id':sid,'base_group':r['base_id'],'condition':r['arm'],'split':r['split'],'source':str(source),
                'source_checksums_sha256':sha256(source/'metadata/checksums.json')}
        try:
            if not dest.exists():build_task_pack(source,dest,count=2,seed=88200,max_expansions=500000)
            contract,episodes=load_task_pack(dest)
            checks=[]
            for ep in episodes:
                task=json.loads((dest/'tasks'/(ep['id']+'.json')).read_text())
                checks.append({'id':ep['id'],'result':verify_delivered_task({k:dest/k/f'cave_{k}.obj' for k in ['visual','collision']},task['planning']['points'],.55)})
            record.update(internal_accepted=len(episodes),internal_rechecks=checks,task_pack=dest.relative_to(ROOT).as_posix())
            if not portal.exists():export_portals(source,portal)
            path=json.loads((portal/'navigation/portal_path.json').read_text())
            record['open_recheck']=verify_delivered_task({k:portal/k/f'cave_{k}.obj' for k in ['visual','collision']},path['points'],.55,closed=False)
            record['open_asset']=portal.relative_to(ROOT).as_posix()
            record['portal_validation']=json.loads((portal/'metadata/portal_validation.json').read_text())
            record['status']='PASS' if record['open_recheck']['status']=='PASS' and all(c['result']['status']=='PASS' for c in checks) else 'FAIL'
        except Exception as exc:record.update(status='FAIL',error=repr(exc));traceback.print_exc()
        records.append(record)
        (ROOT/'preparation.json').write_text(json.dumps({'preregistration_sha256':sha256(PILOT/'preregistration.json'),'scenes':records},indent=2))
        print(sid,record['status'],flush=True)
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pilot',type=Path,default=PILOT)
    parser.add_argument('--output',type=Path,default=ROOT)
    args=parser.parse_args();PILOT=args.pilot;ROOT=args.output;main()
