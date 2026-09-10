import copy
import numpy as np
import pytest

from cave_composer.field import CaveField
from cave_composer.routes import build_routes
from cave_composer.spec import load_spec


def spec(modifiers=None):
    config={'route':[{'straight':18}], 'corridor':{'width':6,'height':5},
            'geology':{'amplitude':.25,'strata':.08,'formations':0},
            'mesh':{'visual_voxel':.3,'collision_voxel':.4}}
    if modifiers is not None:config['morphology']=modifiers
    return load_spec(config)


def field(config,seed=181):
    return CaveField(config,build_routes(config),seed)


def feature(kind='overhang',strength=1):
    return {'id':'ledge','kind':kind,'at':.5,'length':4,'span':2,'depth':2,'strength':strength}


def test_disabled_modules_preserve_exact_mesh():
    baseline=field(spec())
    disabled=field(spec({'cross_section':{'amplitude':0,'eccentricity':0},
                         'roughness':{'contrast':0},'features':[feature(strength=0)]}))
    a,grid_a,origin_a=baseline.mesh(.4);b,grid_b,origin_b=disabled.mesh(.4)
    assert np.array_equal(grid_a,grid_b) and np.array_equal(origin_a,origin_b)
    assert np.array_equal(a.vertices,b.vertices) and np.array_equal(a.faces,b.faces)


def test_all_modules_preserve_protected_core_and_seed():
    config=spec({'cross_section':{'amplitude':.4,'eccentricity':.3},
                 'roughness':{'contrast':1},
                 'features':[dict(feature(k),id=k) for k in
                    ['overhang','ceiling_drop','floor_rise','wall_intrusion','side_cavity','rockfall']]})
    f=field(config);same=field(config)
    rng=np.random.default_rng(72)
    q=rng.normal(size=(2500,3));q[:,0]=0
    q*=rng.uniform(0,f.protected_radius*.99,(len(q),1))/np.linalg.norm(q,axis=1)[:,None]
    radius=np.linalg.norm(q,axis=1);q[:,0]=rng.uniform(2,16,len(q))
    values=f(q)
    assert np.all(values>=f.protected_radius-radius-1e-6)
    assert np.array_equal(values,same(q))
    assert f.morphology.report()==same.morphology.report()


@pytest.mark.parametrize('kind',['overhang','ceiling_drop','floor_rise','wall_intrusion','side_cavity','rockfall'])
def test_feature_changes_void_in_correct_direction(kind):
    base=field(spec());modified=field(spec({'features':[feature(kind)]}))
    rng=np.random.default_rng(37);q=rng.uniform([5,-5,-4],[13,5,4],(9000,3))
    before,after=base(q),modified(q)
    assert np.count_nonzero(np.abs(after-before)>.03)>30
    if kind=='side_cavity':assert np.all(after>=before-1e-6)
    else:assert np.all(after<=before+1e-6)


def test_feature_seed_independent_of_list_order_and_other_modules():
    rock=feature('rockfall');rock['id']='debris'
    a=field(spec({'features':[rock]})).morphology
    b=field(spec({'features':[feature(),rock], 'roughness':{'contrast':.8}})).morphology
    assert a.records[0]==b.records[1]


@pytest.mark.parametrize('config',[
    {'cross_section':{'amplitude':float('nan')}}, {'roughness':{'contrast':1.2}},
    {'cross_section':{'unknown':.2}}, {'features':[dict(feature(),route='missing')]},
    {'features':[feature(),feature()]}, {'features':[dict(feature(),depth=-1)]},
    {'features':[dict(feature('rockfall'),count=2.5)]}, {'features':[dict(feature(),strength=True)]},
])
def test_invalid_controls_rejected(config):
    with pytest.raises(ValueError):spec(config)


def test_named_batch_sampler_is_deterministic_and_preserves_layout():
    from cave_composer.dataset import sample_config, _distribution
    from cave_composer.routes import build_routes
    for seed in [872,873]:
        old=sample_config('train','medium',seed,'topology_v03','branching')
        new=sample_config('train','medium',seed,'morphology_v01','branching')
        assert new==sample_config('train','medium',seed,'morphology_v01','branching')
        assert new['material']==old['material']
        assert all(np.array_equal(a['points'],b['points']) for a,b in zip(build_routes(old),build_routes(new)))
        assert new['sampling']['algorithm']=='morphology_v01'
    override={'overrides':{'morphology':{'features':[]}}}
    with pytest.raises(ValueError):_distribution(override)
    assert _distribution(dict(override,sampler='morphology_v01'))['sampler']=='morphology_v01'
