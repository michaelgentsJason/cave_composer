import hashlib
import json

import numpy as np
from PIL import Image
import pytest

from cave_composer.materials import write_material
from cave_composer.reference_material import read_library
from cave_composer.spec import load_spec


def library(tmp_path):
    entries=[]
    for i in range(3):
        image=np.random.default_rng(i).integers(40,210,(24,24,3),dtype=np.uint8)
        path=tmp_path/f'{i}.png';Image.fromarray(image).save(path)
        entries.append({'id':str(i),'tile':path.name,'tile_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'review_status':'approved_rock_appearance','source_group':'same_cave',
            'attribution':{'title':'Test rock','author':'Test author','source':'test-local','license':'Test only'},
            'crop_xywh':[0,0,24,24]})
    path=tmp_path/'library.json'
    path.write_text(json.dumps({'schema_version':1,'kind':'reviewed_reference_texture_library','entries':entries}))
    return {'style':'limestone','seed':41,'roughness':.8,'texture_library':str(path),
            'texture_library_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'texture_period_metres':1.3}


def test_repeatable_selection_bundles_source_and_attribution(tmp_path):
    spec=library(tmp_path)
    for name in ['a','b']:write_material(spec,tmp_path/name)
    assert (tmp_path/'a/rock_albedo.png').read_bytes()==(tmp_path/'b/rock_albedo.png').read_bytes()
    a=json.loads((tmp_path/'a/material.json').read_text())
    assert a['texture_period_metres']==1.3
    assert a['reference_texture']['source_group']=='same_cave'
    assert 'Test author' in (tmp_path/'a/ATTRIBUTION.txt').read_text()
    original=np.asarray(Image.open(tmp_path/(a['selected_texture_id']+'.png')))
    assert np.array_equal(np.asarray(Image.open(tmp_path/'a/rock_albedo.png')),
        np.rot90(original,a['texture_rotation_degrees']//90))
    # The renderer reads the bundled image; it does not require the library to persist.
    assert Image.open(tmp_path/'a/rock_albedo.png').size==(24,24)


def test_modified_library_and_tile_are_rejected(tmp_path):
    spec=library(tmp_path);path=tmp_path/'library.json';original=path.read_bytes()
    path.write_bytes(original+b' ')
    with pytest.raises(ValueError,match='library checksum'):read_library(spec)
    path.write_bytes(original)
    (tmp_path/'0.png').write_bytes(b'changed')
    with pytest.raises(ValueError,match='tile checksum'):read_library(spec)


def test_explicit_selection_and_seed_diversity(tmp_path):
    spec=library(tmp_path);choices=set()
    for seed in range(12):
        directory=tmp_path/str(seed);write_material({**spec,'seed':seed},directory)
        choices.add(json.loads((directory/'material.json').read_text())['selected_texture_id'])
    assert choices=={'0','1','2'}
    write_material({**spec,'texture_id':'2'},tmp_path/'fixed')
    assert json.loads((tmp_path/'fixed/material.json').read_text())['selected_texture_id']=='2'
    with pytest.raises(ValueError,match='Unknown texture_id'):read_library({**spec,'texture_id':'missing'})


def test_library_path_cannot_escape(tmp_path):
    spec=library(tmp_path);path=tmp_path/'library.json';data=json.loads(path.read_text())
    data['entries'][0]['tile']='../outside.png';path.write_text(json.dumps(data))
    spec['texture_library_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError,match='inside its library'):read_library(spec)


@pytest.mark.parametrize('change',[{'texture_library_sha256':'bad'}, {'seed':1.5},
    {'texture_period_metres':0},{'texture_id':3},{'palette':[[.1]*3]*3}])
def test_reference_config_validation(tmp_path,change):
    spec=library(tmp_path)
    with pytest.raises(ValueError):load_spec({'route':[{'straight':10}],'material':{**spec,**change}})
