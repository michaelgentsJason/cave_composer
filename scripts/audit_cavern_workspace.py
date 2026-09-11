"""Read-only evidence audit. Does not generate caves, change splits or train."""
import argparse,json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cave_composer.bundle import file_sha256,verify_bundle,environment_signature
from cave_composer.tasks import load_task_pack

ROOT=Path(__file__).resolve().parents[1]
PACKS=['branching_stereo','loop','multi_loop']
EVIDENCE=['outputs/pipeline_v04_final/evaluation.json','outputs/pipeline_v04_stereo/stereo_verification.json',
 'exports/morphology_v02/verification.json','exports/morphology_v02/morphology_measurements.json',
 'docs/figures/showcase_hard_v02/validation.json','configs/reference_registry_v01.json',
 'materials/reference_rock_v01/library.json','exports/metashape_crops_v01/validation_exports.json']

def audit(output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    result={'audited_utc':datetime.now(timezone.utc).isoformat(),
        'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'worktree_status':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),
        'source_identity':environment_signature(),'evidence_files':{},'task_packs':[],'morphology_bundles':[],
        'simulator_runtime_verified':False,'policy_evaluated':False,
        'audit_scope':'file integrity and persisted geometric certificates; no new mesh-distance computation or simulator execution'}
    for name in EVIDENCE:
        path=ROOT/name
        result['evidence_files'][name]={'exists':path.is_file(),'sha256':file_sha256(path) if path.is_file() else None}
    for name in PACKS:
        folder=ROOT/'outputs/pipeline_v04_tasks'/name
        contract,episodes=load_task_pack(folder)
        manifest=json.loads((folder/'metadata/manifest.json').read_text())
        result['task_packs'].append({'path':folder.relative_to(ROOT).as_posix(),'manifest_sha256':file_sha256(folder/'metadata/manifest.json'),
            'source_name':manifest['source_name'],'source_split':manifest['source_split'],'requested':manifest['requested'],
            'accepted':len(episodes),'failed':manifest['failed'],'recorded_source_code_hashes':manifest['environment']['source_sha256'],
            'observations':contract['policy_inputs'],'integrity_rechecked':True,'geometry_evidence':'persisted dual-mesh checks validated by load_task_pack'})
    for name in ['before','after','section_only','features_only','rockfall_only','roughness_only']:
        folder=ROOT/'outputs/morphology_v02'/name
        run=verify_bundle(folder);provenance=json.loads((folder/'metadata/provenance.json').read_text())
        result['morphology_bundles'].append({'path':folder.relative_to(ROOT).as_posix(),'integrity_rechecked':True,
            'config_sha256':run['config_sha256'],'checksums_sha256':file_sha256(folder/'metadata/checksums.json'),
            'recorded_generator_version':provenance['composer_version'],'seed':provenance['seed'],
            'recorded_source_code_hashes':provenance['source_sha256']})
    result['summary']={'task_scenes':len(result['task_packs']),'task_requests':sum(p['requested'] for p in result['task_packs']),
        'accepted_tasks':sum(p['accepted'] for p in result['task_packs']),'morphology_bundles':len(result['morphology_bundles'])}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result['summary']))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);audit(parser.parse_args().output)
