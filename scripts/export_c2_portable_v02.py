"""Portable textured derivatives of the new eight-scene interface pilot."""
from pathlib import Path
import argparse,json,sys,subprocess,time,traceback,os,shutil
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cave_composer.bundle import bundle_checksums
from cave_composer.delivery_validation import sha256
ROOT=Path('outputs/c2_pretraining_v02')
BLENDER=None
def main(inset=None):
    suffix='' if inset is None else '_inset005'
    logs=ROOT/('logs'+suffix);logs.mkdir(exist_ok=True);records=[]
    for item in json.loads((ROOT/'preparation.json').read_text())['scenes']:
        sid=item['scene_id'];source=ROOT/item['open_asset'];dest=ROOT/('portable'+suffix)/sid;start=time.perf_counter()
        if inset is not None:
            from cave_composer.portals import export_portals
            source=ROOT/('open_assets'+suffix)/sid
            export_portals(Path(item['source']),source,terminal_inset=inset)
        record={'scene_id':sid,'resolution':1024}
        try:
            audit=[BLENDER,'--background','--python-exit-code','1','--python','cave_composer/blender_audit.py','--','--scene',str(source)]
            with (logs/(sid+'_audit.log')).open('w',encoding='utf-8') as log:subprocess.run(audit,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=90)
            (source/'metadata/checksums.json').write_text(json.dumps(bundle_checksums(source),indent=2))
            command=[BLENDER,'--background','--python-exit-code','1','--python','scripts/export_textured_cave.py','--',
                '--scene',str(source),'--output',str(dest),'--name',sid,'--resolution','1024']
            with (logs/(sid+'_export.log')).open('w',encoding='utf-8') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
            record.update(status='PASS',command=command,glb_sha256=sha256(dest/(sid+'.glb')),obj_sha256=sha256(dest/(sid+'.obj')))
        except Exception as exc:record.update(status='FAIL',error=repr(exc));traceback.print_exc()
        record['seconds']=time.perf_counter()-start;records.append(record)
        (ROOT/('portable_export_runs'+suffix+'.json')).write_text(json.dumps({'terminal_inset_m':inset,'scenes':records},indent=2));print(sid,record['status'],round(record['seconds'],1),flush=True)
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    from verify_textured_exports import verify
    entries=[{'difficulty':'pilot','folder':'portable'+suffix+'/'+r['scene_id'],'name':r['scene_id']} for r in records if r['status']=='PASS']
    verify(ROOT,ROOT/('portable_verification'+suffix+'.json'),entries)
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inset',type=float,choices=[.05])
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--blender',default=os.environ.get('BLENDER_PATH') or shutil.which('blender'))
    args=parser.parse_args();ROOT=args.root;BLENDER=args.blender
    if not BLENDER:parser.error('Supply --blender, BLENDER_PATH, or blender on PATH')
    main(args.inset)
