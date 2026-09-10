"""Build/resume a matched morphology comparison from its six saved configs."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cave_composer.bundle import bundle_checksums, verify_bundle, verify_portal_export
from cave_composer.pipeline import generate, attach_intersection_audit, dump
from cave_composer.portals import export_portals
from cave_composer.spec import load_spec
from scripts.expand_difficulty_exports import blender_run
from scripts.measure_morphology import main as measure
from scripts.package_morphology_comparison import main as package

CASES=['before','after','section_only','roughness_only','features_only','rockfall_only']


def build(configs,source,exports,blender,seed=97001):
    configs,source,exports=map(Path,[configs,source,exports])
    source.mkdir(parents=True,exist_ok=True);exports.mkdir(parents=True,exist_ok=True)
    for name in CASES:
        folder=source/name;config=load_spec(configs/(name+'.json'))
        if folder.exists():
            verify_bundle(folder)
            saved=json.loads((folder/'metadata/config.json').read_text())
            provenance=json.loads((folder/'metadata/provenance.json').read_text())
            if saved!=config or provenance['seed']!=seed:
                raise ValueError(f'Existing scene does not match requested config/seed: {folder}')
        else:
            generate(config,seed,str(folder))
        print(name,'bundle verified',flush=True)
    measure(source)
    for name in ['before','after']:
        folder=source/name
        if not (folder/'metadata/intersection_audit.json').exists():
            blender_run(blender,'cave_composer/blender_audit.py',['--scene',folder],source/(name+'_audit.log'))
            validation=json.loads((folder/'metadata/validation.json').read_text())
            audit=json.loads((folder/'metadata/intersection_audit.json').read_text())
            attach_intersection_audit(validation,audit)
            if validation['status']!='VALID':raise ValueError(f'Closed audit failed: {name}')
            dump(folder/'metadata/validation.json',validation)
            dump(folder/'metadata/checksums.json',bundle_checksums(folder))
        opened=source/(name+'_open')
        if not opened.exists():export_portals(folder,opened)
        verify_portal_export(opened)
        if not (opened/'metadata/intersection_audit.json').exists():
            blender_run(blender,'cave_composer/blender_audit.py',['--scene',opened],source/(name+'_open_audit.log'))
            dump(opened/'metadata/checksums.json',bundle_checksums(opened))
        for reference in [folder,opened]:
            if json.loads((reference/'metadata/intersection_audit.json').read_text())['status']!='PASS':
                raise ValueError(f'Mesh intersection audit failed: {reference}')
        if not (exports/name).exists():
            blender_run(blender,'scripts/export_textured_cave.py',
                        ['--scene',opened,'--output',exports/name,'--name',name],source/(name+'_export.log'))
        print(name,'portable export complete',flush=True)
    if not (exports/'render_views.json').exists():
        blender_run(blender,'scripts/render_morphology_comparison.py',['--root',exports],source/'render_comparison.log')
    package(exports,source)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--configs',default='configs/morphology_v02')
    p.add_argument('--source',default='outputs/morphology_v02')
    p.add_argument('--exports',default='exports/morphology_v02')
    p.add_argument('--blender',default='D:/Blender/blender.exe')
    p.add_argument('--seed',type=int,default=97001)
    a=p.parse_args();build(a.configs,a.source,a.exports,a.blender,a.seed)
