import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cave_composer.handoff import create_handoff,preflight

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packs',nargs='+');p.add_argument('--profile',default='research_workspace/contracts/platform_proposal_v01.json')
    p.add_argument('--output');p.add_argument('--dataset-id',default='cavern_interface_review_v01');p.add_argument('--check');p.add_argument('--require-runtime',action='store_true');a=p.parse_args()
    if a.check:r=preflight(a.check,a.require_runtime)
    else:
        if not a.packs or not a.output:p.error('--packs and --output required for new delivery')
        r=create_handoff(a.packs,a.profile,a.output,a.dataset_id)
    print(json.dumps(r,indent=2))
