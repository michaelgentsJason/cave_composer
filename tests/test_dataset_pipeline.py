"""Exercise real small bundles through interruptions, corruption and same-seed retry."""
import json
from pathlib import Path
import pytest
from cave_composer import dataset,pipeline
from cave_composer.bundle import dataset_lock,file_sha256,verify_bundle
from cave_composer.spec import load_spec


@pytest.fixture
def small_distribution(monkeypatch):
    def sample(split,difficulty,seed):
        return load_spec({'name':f'test_{seed}','split':split,'route':[{'straight':9}],
                          'geology':{'amplitude':.15,'strata':.06,'formations':0},
                          'mesh':{'visual_voxel':.34,'collision_voxel':.34}})
    monkeypatch.setattr(dataset,'sample_config',sample)
    return {'split':'train','base_seed':23000}


def read_manifest(root):
    return json.loads((root/'manifest.json').read_text(encoding='utf-8'))


def test_interrupt_resume_extend_and_skip_verified_scenes(tmp_path,monkeypatch,small_distribution):
    root=tmp_path/'dataset'
    original=dataset._job
    calls=[]
    def interrupted(payload):
        calls.append(payload[1])
        if len(calls)==2: raise KeyboardInterrupt()
        return original(payload)
    monkeypatch.setattr(dataset,'_job',interrupted)
    with pytest.raises(KeyboardInterrupt):
        dataset.generate_dataset(small_distribution,2,output=root)
    manifest=read_manifest(root)
    assert manifest['status']=='INTERRUPTED' and manifest['valid']==1 and manifest['pending']==1
    assert (root/'index.html').exists()
    first=root/'scene_000000/visual/cave_visual.obj'
    before=(file_sha256(first),first.stat().st_mtime_ns)
    monkeypatch.setattr(dataset,'_job',original)
    resumed=dataset.generate_dataset(small_distribution,3,output=root,resume=True)
    assert resumed['valid']==3 and resumed['pending']==0
    assert resumed['runs'][-1]['reused']==1 and resumed['runs'][-1]['scheduled']==2
    assert (file_sha256(first),first.stat().st_mtime_ns)==before
    for record in resumed['records']: verify_bundle(root/record['path'])
    noop=dataset.generate_dataset(small_distribution,3,output=root,resume=True)
    assert noop['runs'][-1]['scheduled']==0 and noop['runs'][-1]['reused']==3
    assert (file_sha256(first),first.stat().st_mtime_ns)==before


def test_recover_completed_bundle_before_manifest_acknowledgement(tmp_path,monkeypatch,small_distribution):
    root=tmp_path/'dataset';original=dataset._job
    def crash_after_commit(payload):
        result=original(payload)
        assert result['status']=='VALID'
        raise KeyboardInterrupt()
    monkeypatch.setattr(dataset,'_job',crash_after_commit)
    with pytest.raises(KeyboardInterrupt): dataset.generate_dataset(small_distribution,1,output=root)
    assert read_manifest(root)['valid']==0
    monkeypatch.setattr(dataset,'_job',lambda payload: pytest.fail('Completed bundle must be recovered without regeneration'))
    result=dataset.generate_dataset(small_distribution,1,output=root,resume=True)
    assert result['valid']==1 and result['runs'][-1]['reused']==1


def test_interrupt_inside_scene_archives_partial_before_rebuilding(tmp_path,monkeypatch,small_distribution):
    root=tmp_path/'dataset';original=pipeline.CaveField.mesh
    def interrupted(*args,**kwargs):raise KeyboardInterrupt()
    monkeypatch.setattr(pipeline.CaveField,'mesh',interrupted)
    with pytest.raises(KeyboardInterrupt):dataset.generate_dataset(small_distribution,1,output=root)
    partial=root/'scene_000000.failed'
    run=json.loads((partial/'metadata/run.json').read_text(encoding='utf-8'))
    assert run['status']=='INTERRUPTED' and run['stages'][-1]['name']=='geometry'
    monkeypatch.setattr(pipeline.CaveField,'mesh',original)
    result=dataset.generate_dataset(small_distribution,1,output=root,resume=True)
    record=result['records'][0]
    assert record['status']=='VALID' and record['attempts']==2
    assert (root/record['history'][0]/'metadata/failure.json').is_file()
    assert not partial.exists()


def test_explicit_retry_preserves_failure_and_seed(tmp_path,monkeypatch,small_distribution):
    root=tmp_path/'dataset';original=pipeline.write_material
    def unavailable(*args,**kwargs): raise OSError('Injected transient material write failure')
    monkeypatch.setattr(pipeline,'write_material',unavailable)
    failed=dataset.generate_dataset(small_distribution,1,output=root)
    assert failed['invalid']==1 and failed['errors']==1
    assert failed['records'][0]['failed_stage']=='material_and_export'
    seed=failed['records'][0]['seed']
    monkeypatch.setattr(pipeline,'write_material',original)
    kept=dataset.generate_dataset(small_distribution,1,output=root,resume=True)
    assert kept['invalid']==1 and kept['runs'][-1]['scheduled']==0
    fixed=dataset.generate_dataset(small_distribution,1,output=root,resume=True,retry_failed=True)
    record=fixed['records'][0]
    assert record['status']=='VALID' and record['attempts']==2 and record['seed']==seed
    assert len(record['history'])==1
    assert (root/record['history'][0]/'metadata/failure.json').is_file()
    verify_bundle(root/record['path'])


def test_resume_rejects_tampering_and_changed_contract(tmp_path,small_distribution):
    root=tmp_path/'dataset';dataset.generate_dataset(small_distribution,1,output=root)
    with pytest.raises(ValueError,match='contract mismatch'):
        dataset.generate_dataset({**small_distribution,'base_seed':24000},1,output=root,resume=True)
    obj=root/'scene_000000/visual/cave_visual.obj'
    obj.write_bytes(obj.read_bytes()+b'\n# unrecorded edit\n')
    changed=file_sha256(obj)
    with pytest.raises(ValueError,match='integrity mismatch'):
        dataset.generate_dataset(small_distribution,1,output=root,resume=True,retry_failed=True)
    assert file_sha256(obj)==changed


@pytest.mark.parametrize('distribution',[None,{}, {'split':'train','base_seed':1.5},
    {'base_seed':True},{'schema_version':2},{'overrides':{'route':[{'straight':9}]}}])
def test_invalid_request_does_not_create_dataset(tmp_path,distribution):
    root=tmp_path/'invalid'
    # {} is valid distribution shorthand; the invalid worker argument still must preflight.
    with pytest.raises(ValueError):
        dataset.generate_dataset(distribution,1,workers=0 if distribution=={} else 1,output=root)
    assert not root.exists()


def test_lock_is_exclusive_and_released(tmp_path):
    with dataset_lock(tmp_path):
        with pytest.raises(RuntimeError,match='Another dataset process'):
            with dataset_lock(tmp_path): pass
    with dataset_lock(tmp_path): pass


def test_render_options_fail_before_geometry(tmp_path):
    config={'route':[{'straight':9}]}
    with pytest.raises(ValueError,match='requires render'):
        pipeline.generate(config,output=tmp_path/'no_render',save_blend=True)
    with pytest.raises(ValueError,match='Blender not found'):
        pipeline.generate(config,output=tmp_path/'bad_blender',render=True,blender=str(tmp_path/'missing.exe'))
    assert not (tmp_path/'no_render').exists() and not (tmp_path/'bad_blender').exists()
