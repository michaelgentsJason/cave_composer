"""Pinned local texture-library selection, independent of scene geometry."""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


def read_library(spec):
    path=Path(spec['texture_library']).resolve()
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=spec['texture_library_sha256']:
        raise ValueError('Texture library checksum mismatch; explicitly repin reviewed changes')
    data=json.loads(raw)
    if data.get('schema_version')!=1 or data.get('kind')!='reviewed_reference_texture_library':
        raise ValueError('Unsupported reference texture library')
    entries=data.get('entries',[])
    if not entries or len({e['id'] for e in entries})!=len(entries):
        raise ValueError('Texture library must contain unique entries')
    for entry in entries:
        if entry.get('review_status')!='approved_rock_appearance':
            raise ValueError('Texture entry has not been reviewed')
        tile=(path.parent/entry['tile']).resolve()
        if path.parent not in tile.parents or not tile.is_file():
            raise ValueError('Texture path must stay inside its library')
        if hashlib.sha256(tile.read_bytes()).hexdigest()!=entry['tile_sha256']:
            raise ValueError('Reference tile checksum mismatch: '+entry['id'])
    if 'texture_id' in spec and spec['texture_id'] not in {e['id'] for e in entries}:
        raise ValueError('Unknown texture_id: '+spec['texture_id'])
    return path,sorted(entries,key=lambda e:e['id'])


def write_reference_material(spec,directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    library,entries=read_library(spec)
    rng=np.random.default_rng(int(spec['seed']))
    entry=next(e for e in entries if e['id']==spec['texture_id']) if 'texture_id' in spec else entries[int(rng.integers(len(entries)))]
    rotation=int(rng.integers(4))
    with Image.open(library.parent/entry['tile']) as im:
        rgb=np.rot90(np.asarray(im.convert('RGB')),rotation).copy()
    Image.fromarray(rgb).save(directory/'rock_albedo.png')
    palette=np.quantile(rgb.reshape(-1,3)/255.,[.15,.5,.85],axis=0)
    metadata={**spec,'palette':palette.tolist(),'water_baked':False,
        'texture_period_metres':spec.get('texture_period_metres',1.5),
        'method':'reviewed scan-image patch; periodic preprocessing; seeded quarter-turn; box projection',
        'selected_texture_id':entry['id'],'texture_rotation_degrees':rotation*90,
        'reference_texture':entry,'library_sha256':spec['texture_library_sha256'],
        'normal_inferred':False,'roughness_inferred':False,'intrinsic_albedo_recovered':False}
    (directory/'material.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    credit=entry['attribution']
    (directory/'ATTRIBUTION.txt').write_text(
        f"{credit.get('title','')}\n{credit.get('author','')}\n{credit.get('source','')}\n"
        f"License: {credit.get('license','')}\n"
        f"Changes: cropped at {entry['crop_xywh']}; periodic boundary processing; rotation {rotation*90} degrees; box projection and optional UV baking.\n"
        'Source is a captured-color atlas, not a measured intrinsic/PBR material. Normal detail and roughness are procedural/configured.\n',encoding='utf-8')
    return palette
