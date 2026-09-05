"""Restyle a completed bundle while preserving visual/collision mesh bytes."""
from pathlib import Path
import json,shutil,subprocess,hashlib,time
from .materials import write_material
from .spec import load_spec,merge
from .pipeline import dump,digest


def restyle(source,material,output,blender=None):
    source=Path(source).resolve(); output=Path(output).resolve()
    if output.exists(): raise FileExistsError(output)
    if not (source/'.cave_composer_bundle').exists(): raise ValueError('Source is not a Cave Composer bundle')
    output.mkdir(parents=True)
    (output/'.cave_composer_bundle').write_text('1\n')
    for directory in ['visual','collision','navigation','metadata']:
        shutil.copytree(source/directory,output/directory)
    (output/'previews').mkdir()
    shutil.copy2(source/'previews/topology.png',output/'previews/topology.png')
    config=load_spec(source/'metadata/config.yaml'); config['material']=merge(config['material'],material); config=load_spec(config)
    write_material(config['material'],output/'materials')
    dump(output/'metadata/config.json',config)
    import yaml
    (output/'metadata/config.yaml').write_text(yaml.safe_dump(config,sort_keys=False),encoding='utf-8')
    before=json.loads((source/'metadata/provenance.json').read_text())
    before['appearance_sha256']=digest(config['material'])
    before['restyled_from']=str(source); before['appearance_only']=True
    checks={}
    for kind in ['visual','collision']:
        for filename in ['mesh.npz',f'cave_{kind}.obj']:
            rel=Path(kind)/filename
            checks[str(rel)]=hashlib.sha256((source/rel).read_bytes()).hexdigest()==hashlib.sha256((output/rel).read_bytes()).hexdigest()
    if not all(checks.values()): raise RuntimeError('Restyling changed geometry bytes')
    dump(output/'metadata/provenance.json',before)
    dump(output/'metadata/appearance_experiment.json',{'geometry_byte_identity':checks,'material':config['material'],'result':'appearance prior only; no copied scan geometry or image atlas'})
    if blender:
        with (output/'metadata/restyle_render.log').open('w') as log:
            subprocess.run([blender,'--background','--python-exit-code','1','--python',str(Path(__file__).parent/'blender_render.py'),'--','--scene',str(output),'--save-blend'],stdout=log,stderr=subprocess.STDOUT,check=True)
    dump(output/'metadata/checksums.json',{str(p.relative_to(output)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.rglob('*')) if p.is_file() and p.name!='checksums.json'})
    return output
