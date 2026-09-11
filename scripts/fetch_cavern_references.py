"""Fetch primary-source citation metadata. No inferred publication venues."""
import hashlib,html,json,re,urllib.request
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PAPERS={'garcia2025plume':'2508.20926','tobin2017randomization':'1703.06907',
        'schulman2017ppo':'1707.06347','kim2026flashsac':'2604.04539','nvidia2025isaaclab':'2511.04831'}

def fetch(url):
    errors=[]
    for proxy in [None,'http://127.0.0.1:7897']:
        try:
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({} if proxy is None else {'https':proxy,'http':proxy}))
            with opener.open(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=20) as r:return r.read()
        except Exception as exc:errors.append(str(exc))
    raise RuntimeError(errors)

def main():
    out=ROOT/'research_workspace/bibliography';out.mkdir(parents=True,exist_ok=True)
    entries=[];records=[]
    for key,aid in PAPERS.items():
        path=out/f'{aid}.html'
        if not path.exists():path.write_bytes(fetch('https://arxiv.org/abs/'+aid))
        raw=path.read_bytes();text=raw.decode()
        meta={}
        for tag in re.findall(r'<meta\b[^>]*>',text,re.I):
            attrs=dict(re.findall(r'(\w+)="([^"]*)"',tag))
            if 'name' in attrs and 'content' in attrs:meta.setdefault(attrs['name'],[]).append(html.unescape(attrs['content']))
        authors=[('{NVIDIA}' if a=='NVIDIA' else a) for a in meta['citation_author'] if a.strip() != ':'];title=meta['citation_title'][0];year=meta['citation_date'][0][:4]
        # Primary author metadata is retained in verification.json; standard et al. in print.
        print_authors=authors[:6]+['others'] if len(authors)>8 else authors
        entry=f'@article{{{key},\n  title={{{{{title}}}}},\n  author={{{" and ".join(print_authors)}}},\n  journal={{arXiv preprint arXiv:{aid}}},\n  year={{{year}}},\n}}\n'
        entries.append(entry)
        records.append({'key':key,'url':'https://arxiv.org/abs/'+aid,'source_sha256':hashlib.sha256(raw).hexdigest(),
            'verified_utc':datetime.now(timezone.utc).isoformat(),'title':title,'authors':authors,'year':year,
            'status':'primary_metadata_verified','venue_scope':'arXiv version cited; publication upgrade deferred pending verification'})
        print(key,title,flush=True)
    target=ROOT/'overleaf/refs.bib'
    if target.exists():raise FileExistsError(target)
    target.write_text('\n'.join(entries),encoding='utf-8')
    (out/'verification.json').write_text(json.dumps(records,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

if __name__=='__main__':main()
