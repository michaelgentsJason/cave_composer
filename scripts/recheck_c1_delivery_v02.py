"""Correct OBJ seam incidence without rerunning or modifying any pilot mesh."""
from pathlib import Path
import argparse,json,sys,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cave_composer.delivery_validation import verify_delivered_task,sha256
ROOT=Path('outputs/c1_pilot_v02')
def main(output=None):
    target=output or ROOT/'delivery_recheck.json'
    if target.exists():raise FileExistsError(target)
    records=[]
    for path in sorted((ROOT/'results').glob('*.json')):
        r=json.loads(path.read_text());item={'original_result':path.relative_to(ROOT).as_posix(),'original_sha256':sha256(path)}
        scene=ROOT/r['request']['scene'];p=r.get('planning',{})
        began=time.perf_counter()
        if p.get('points'):
            item['delivered_check']=verify_delivered_task({k:scene/k/f'cave_{k}.obj' for k in ['visual','collision']},p['points'],.55)
        item['seconds']=time.perf_counter()-began
        item['accepted']=(r.get('generation_status')=='VALID' and p.get('status')=='PASS' and item.get('delivered_check',{}).get('status')=='PASS')
        records.append(item)
        print(r['request']['base_id'],r['request']['arm'],item['accepted'],r.get('failed_generation_checks'),p.get('reason'),flush=True)
    report={'interoperability_correction':'Initial importer retained UV/normal split vertices; exact-position welding restores triangle incidence. Original first checks retained. No geometry regeneration, triangle movement or new seeds.',
            'checker_sha256':sha256('cave_composer/delivery_validation.py'),'results':records}
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,indent=2))
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args();ROOT=args.root;main(args.output)
