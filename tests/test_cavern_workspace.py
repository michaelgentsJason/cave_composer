"""Evidence-integrity regressions: no simulator or learner is involved."""
import copy
import json
from pathlib import Path
import pytest
from cave_composer.bundle import file_sha256
from cave_composer.handoff import contained, preflight, validate_results, write_new
from scripts.audit_cavern_sources import audit
from scripts.check_cavern_paper import submission_blockers

@pytest.fixture
def receipt(tmp_path):
    trajectory=tmp_path/'trajectory.json';trajectory.write_text('{"test_fixture":true}')
    sha=file_sha256(trajectory)
    run={k:sha for k in ['checkpoint_sha256','dataset_manifest_sha256','config_sha256',
        'normalizer_sha256','preprocessing_sha256','episode_manifest_sha256']}
    run.update(algorithm='FlashSAC',dataset_id='fixture',training_seed=0,inference_rule='fixture',
        policy_frozen=True,in_episode_interventions=0,episodes_fixed_before_policy_evaluation=True)
    episodes=[{'episode_id':'e0','scene_id':'s0'}]
    row=dict(episode_id='e0',scene_id='s0',dataset_id='fixture',checkpoint_sha256=sha,
        outcome='collision',success=False,collision=True,out_of_bounds=False,timeout=False,
        elapsed_seconds=1.,remaining_traversable_distance_m=None,
        remaining_traversable_distance_m_reason='no estimator in unit fixture',
        remaining_distance_method='unavailable',trajectory='trajectory.json',trajectory_sha256=sha)
    return run,episodes,row,tmp_path

def test_valid_receipt_is_not_policy_verification(receipt):
    run,eps,row,root=receipt
    result=validate_results([row],run,eps,root)
    assert result['status']=='adapter_checked' and result['policy_evaluated'] is False

@pytest.mark.parametrize('mutation', ['missing_episode','duplicate_episode','checkpoint_switch','dataset_switch',
    'nan_time','negative_distance','contradictory_outcome','missing_distance_reason','escaping_trajectory',
    'tampered_trajectory','policy_not_frozen','intervention','no_preselection','duplicate_schedule'])
def test_bad_receipts_rejected(receipt,mutation):
    run,eps,row,root=receipt;rows=[row]
    if mutation=='missing_episode':rows=[]
    elif mutation=='duplicate_episode':rows=[row,row]
    elif mutation=='checkpoint_switch':row['checkpoint_sha256']='0'*64
    elif mutation=='dataset_switch':row['dataset_id']='other'
    elif mutation=='nan_time':row['elapsed_seconds']=float('nan')
    elif mutation=='negative_distance':row['remaining_traversable_distance_m']=-1
    elif mutation=='contradictory_outcome':row['success']=True
    elif mutation=='missing_distance_reason':row.pop('remaining_traversable_distance_m_reason')
    elif mutation=='escaping_trajectory':row['trajectory']='../outside.json'
    elif mutation=='tampered_trajectory':(root/'trajectory.json').write_text('changed')
    elif mutation=='policy_not_frozen':run['policy_frozen']=False
    elif mutation=='intervention':run['in_episode_interventions']=1
    elif mutation=='no_preselection':run['episodes_fixed_before_policy_evaluation']=False
    elif mutation=='duplicate_schedule':eps=eps+eps
    with pytest.raises((ValueError,KeyError)):validate_results(rows,run,eps,root)

def test_not_run_retained_without_invented_metrics(receipt):
    run,eps,row,root=receipt
    row.update(outcome='not_run',collision=False,elapsed_seconds=None,
        elapsed_seconds_reason='simulator unavailable',not_run_reason='simulator unavailable')
    row.pop('trajectory');row.pop('trajectory_sha256')
    assert validate_results([row],run,eps,root)['executed']==0
    row['elapsed_seconds']=0
    with pytest.raises(ValueError):validate_results([row],run,eps,root)

def test_write_new_and_path_containment(tmp_path):
    target=tmp_path/'f.json';write_new(target,{'frozen':True})
    with pytest.raises(FileExistsError):write_new(target,{'frozen':False})
    with pytest.raises(ValueError):contained(tmp_path,'../escape')
    with pytest.raises(ValueError):contained(tmp_path,str(tmp_path/'absolute'))

def test_snapshot_tamper_is_rejected_before_loader(tmp_path):
    write_new(tmp_path/'asset.json',{'value':1})
    manifest={'files':{'asset.json':file_sha256(tmp_path/'asset.json')}}
    write_new(tmp_path/'manifest.json',manifest)
    write_new(tmp_path/'manifest_digest.json',{'sha256':file_sha256(tmp_path/'manifest.json')})
    (tmp_path/'asset.json').write_text('{"value":2}')
    with pytest.raises(ValueError,match='Asset hash mismatch'):preflight(tmp_path)

def test_source_usage_cannot_be_relabelled_untouched():
    source=dict(group_id='g',asset_ids=['x'],identity_confirmed=True,
        prior_or_development_used=True,training_use='never_used_confirmed',untouched_final_eligible=True)
    with pytest.raises(ValueError):audit({'sources':[source]})
    source['prior_or_development_used']=False;source['identity_confirmed']=False
    with pytest.raises(ValueError):audit({'sources':[source]})

def test_rehashed_delivery_cannot_change_certified_endpoint(tmp_path,monkeypatch):
    task={'id':'t0','start':{'position_m':[0,0,0]},'goal':{'position_m':[1,0,0]}}
    monkeypatch.setattr('cave_composer.handoff.load_task_pack',lambda folder:({},[task]))
    (tmp_path/'pack').mkdir()
    episode={'episode_id':'s/t0','scene_id':'s','task_id':'t0','source_group':'g','split':'train',
        'reset':task['start'],'goal':{'position_m':[99,0,0]},'task_kind':'interior_pair_not_full_exit'}
    write_new(tmp_path/'episodes.json',{'episodes':[episode]})
    write_new(tmp_path/'profile.json',{'status':'UNCONFIRMED'})
    m={'files':{n:file_sha256(tmp_path/n) for n in ['episodes.json','profile.json']},
        'scenes':[{'scene_id':'s','source_group':'g','split':'train','task_pack':'pack'}],
        'episodes':'episodes.json','profile':'profile.json'}
    write_new(tmp_path/'manifest.json',m)
    write_new(tmp_path/'manifest_digest.json',{'sha256':file_sha256(tmp_path/'manifest.json')})
    with pytest.raises(ValueError,match='differs from validated task'):preflight(tmp_path)

def test_submission_gate_keeps_missing_evidence_and_human_reviews():
    claims={'claims':[{'id':'C3','required_for_submission':True,'status':'blocked'}]}
    blockers=submission_blockers('Results: \\missing. TODO',claims,{})
    assert 'unresolved_text_or_result_placeholders' in blockers
    assert 'evidence_pending:C3' in blockers
    assert 'human_review_pending:final_submission_authorized' in blockers
