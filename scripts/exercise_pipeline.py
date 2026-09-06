"""Reproducible multi-split pipeline acceptance run, including resume and appearance independence."""
import argparse
import json
from pathlib import Path
import sys
import time
import yaml
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cave_composer.dataset import generate_dataset
from cave_composer.bundle import atomic_json,file_sha256,verify_bundle


def build_collection_index(root):
    root=Path(root)
    cards=[]
    for folder in sorted(root.iterdir()):
        if not (folder/'manifest.json').is_file():continue
        manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        thumbnail=next(folder.glob('scene_*/previews/overview.png'),None)
        image=f'<img src="{thumbnail.relative_to(root).as_posix()}" alt="{folder.name} overview">' if thumbnail else ''
        cards.append(f'<article><a href="{folder.name}/index.html">{image}<h2>{folder.name}</h2></a><p>{manifest["valid"]} valid / {manifest["requested"]} requested · {manifest["invalid"]} failed</p><a href="{folder.name}/metrics.csv">Metrics CSV</a> · <a href="{folder.name}/manifest.json">Run history</a></article>')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Cave Composer pipeline review</title><style>:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#101b22;color:#e8f0f3}body{max-width:1250px;margin:36px auto;padding:0 20px}h1{font-size:38px}p{color:#b5c6d0;line-height:1.6}a{color:#8bd7c8}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:22px}article{padding:18px;background:#1b2a33;border:1px solid #344a57;border-radius:10px}img{width:100%;aspect-ratio:1.6;object-fit:contain}h2{font-size:22px;margin:12px 0}</style><body><h1>Automated cave pipeline</h1><p>Five dataset splits, same-seed resume and CAVERS appearance variants. Open a collection to inspect individual geometry, validation, stage logs and previews.</p><p><a href="acceptance.json">Acceptance evidence</a> · <a href="../../docs/pipeline.md">Pipeline guide</a></p><div class="grid">'''+''.join(cards)+'''</div></body></html>'''
    (root/'index.html').write_text(page,encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='outputs/pipeline_v02')
    parser.add_argument('--blender')
    parser.add_argument('--workers',type=int,default=2)
    parser.add_argument('--base-seed',type=int,default=24000)
    parser.add_argument('--material-prior',default='outputs/material_experiment/cavers_transfer/cavers_style.json')
    args=parser.parse_args()
    root=Path(args.output);root.mkdir(parents=True,exist_ok=True)
    distributions=root/'distributions';distributions.mkdir(exist_ok=True)
    start=time.perf_counter()
    results=[]
    render=bool(args.blender)
    options={'workers':args.workers,'render':render,'blender':args.blender,'save_blend':render}
    for split,count in [('train',8),('validation',4),('id_test',4),('ood_geometry',4),('ood_composition',4)]:
        config={'schema_version':1,'split':split,'difficulty':'medium','base_seed':args.base_seed}
        (distributions/f'{split}.yaml').write_text(yaml.safe_dump(config),encoding='utf-8')
        folder=root/split
        if split=='train' and not folder.exists():
            generate_dataset(config,4,output=folder,**options)
        before={str(p):[file_sha256(p),p.stat().st_mtime_ns] for p in folder.glob('scene_*/visual/cave_visual.obj')}
        manifest=generate_dataset(config,count,output=folder,resume=folder.exists(),**options)
        assert all([file_sha256(Path(p)),Path(p).stat().st_mtime_ns]==value for p,value in before.items())
        for record in manifest['records']:
            if record['status']=='VALID':verify_bundle(folder/record['path'])
        results.append({'split':split,'requested':count,'valid':manifest['valid'],'invalid':manifest['invalid'],
                        'errors':manifest['errors'],'existing_meshes_untouched':len(before),
                        'latest_run':manifest['runs'][-1]})
        atomic_json(root/'progress.json',{'splits':results,'elapsed_seconds':time.perf_counter()-start})
    appearance=None
    prior_path=Path(args.material_prior)
    if prior_path.is_file():
        material=json.loads(prior_path.read_text(encoding='utf-8'))
        config={'schema_version':1,'split':'train','difficulty':'medium','base_seed':args.base_seed,
                'overrides':{'material':material}}
        (distributions/'cavers.yaml').write_text(yaml.safe_dump(config,sort_keys=False),encoding='utf-8')
        folder=root/'cavers'
        manifest=generate_dataset(config,2,output=folder,resume=folder.exists(),**options)
        pairs=[]
        for record in manifest['records']:
            name=record['path'];baseline=root/'train'/name;styled=folder/name
            checks={rel:file_sha256(baseline/rel)==file_sha256(styled/rel) for rel in
                    ['visual/cave_visual.obj','visual/mesh.npz','collision/cave_collision.obj','collision/mesh.npz']}
            assert all(checks.values())
            assert file_sha256(baseline/'materials/rock_albedo.png')!=file_sha256(styled/'materials/rock_albedo.png')
            pairs.append({'scene':name,'geometry_byte_identity':checks,'albedo_changed':True})
        appearance={'requested':2,'valid':manifest['valid'],'invalid':manifest['invalid'],'pairs':pairs}
    result={'splits':results,'appearance':appearance,'rendered':render,'elapsed_seconds':time.perf_counter()-start,
            'scope':'pipeline stability smoke test; not a throughput benchmark or simulator test'}
    atomic_json(root/'acceptance.json',result)
    build_collection_index(root)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
