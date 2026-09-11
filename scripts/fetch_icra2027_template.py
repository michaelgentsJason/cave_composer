"""Download official template bytes with provenance; never overwrite snapshots."""
import hashlib,json,shutil,urllib.request,zipfile
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/'overleaf'
URLS={
 'ieeeconf.zip':'https://ras.papercept.net/conferences/support/files/ieeeconf.zip',
 'IEEEtranBST.zip':'https://ras.papercept.net/conferences/support/files/IEEEtranBST.zip',
 'icra2027_call.html':'https://2027.ieee-icra.org/contribute/call-for-icra-2027-papers-now-accepting-submissions/',
 'papercept_tex.html':'https://ras.papercept.net/conferences/support/tex.php'}

def main():
    original=ROOT/'template_original';original.mkdir(parents=True,exist_ok=True)
    record=original/'provenance.json'
    if record.exists():
        data=json.loads(record.read_text())
        for name,item in data['files'].items():assert hashlib.sha256((original/name).read_bytes()).hexdigest()==item['sha256']
        print('Existing official snapshot verified; no redownload');return
    data={'downloaded_utc':datetime.now(timezone.utc).isoformat(),'files':{}}
    for name,url in URLS.items():
        path=original/name
        if path.exists():raise FileExistsError(path)
        errors=[]
        for proxy in [None,'http://127.0.0.1:7897']:
            try:
                opener=urllib.request.build_opener(urllib.request.ProxyHandler({} if proxy is None else {'http':proxy,'https':proxy}))
                with opener.open(urllib.request.Request(url,headers={'User-Agent':'CaveComposer research template fetch'}),timeout=25) as response:
                    raw=response.read();final=response.url
                break
            except Exception as exc:errors.append(str(exc))
        else:raise RuntimeError(errors)
        path.write_bytes(raw);data['files'][name]={'url':url,'resolved_url':final,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'downloaded_utc':datetime.now(timezone.utc).isoformat()}
        print(name,len(raw),flush=True)
    for name in ['ieeeconf.zip','IEEEtranBST.zip']:
        with zipfile.ZipFile(original/name) as bundle:
            dest=original/Path(name).stem;dest.mkdir()
            for member in bundle.infolist():
                target=(dest/member.filename).resolve()
                if not target.is_relative_to(dest.resolve()):raise ValueError('Unsafe zip path')
            bundle.extractall(dest)
    for filename in ['ieeeconf.cls','IEEEtran.bst']:
        matches=list(original.rglob(filename));assert len(matches)==1,matches
        target=ROOT/filename
        if target.exists():raise FileExistsError(target)
        shutil.copyfile(matches[0],target)
    record.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
