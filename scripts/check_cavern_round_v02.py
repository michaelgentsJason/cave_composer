"""Final local evidence consistency and source-only ZIP compilation check."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET
import yaml

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/cavern_round_v02'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    checked=[]
    ledger=yaml.safe_load((ROOT/'overleaf/CLAIM_EVIDENCE.yaml').read_text(encoding='utf-8'))
    for claim in ledger['claims']:
        for item in claim.get('raw_artifacts',[]):
            path=ROOT/item['path']
            if not path.is_file() or sha(path)!=item['sha256']:raise ValueError('Claim artifact mismatch: '+str(path))
            checked.append(item['path'])
    for name in ['provenance.json','composition_provenance.json']:
        doc=json.loads((ROOT/'overleaf/figures/generated/c1_v02'/name).read_text())
        for p,digest in doc['inputs'].items():
            if sha(ROOT/p)!=digest:raise ValueError('Figure input changed: '+p)
    raw=json.loads((ROOT/'outputs/c1_pilot_v02/delivery_recheck.json').read_text())['results']
    summary=json.loads((ROOT/'outputs/c1_pilot_v02/summary.json').read_text())
    if len(raw)!=18 or len(summary['rows'])!=18:raise ValueError('Pilot denominator changed')
    if sum(r['accepted'] for r in raw)!=sum(g['final_passes'] for g in summary['groups']):raise ValueError('Recheck/summary yield differs')
    gallery=(OUT/'index.html').read_text(encoding='utf-8')
    links=re.findall(r'(?:href|src)="([^"]+)"',gallery)
    for rel in links:
        if not (OUT/rel).is_file():raise ValueError('Gallery link missing: '+rel)
    archive=ROOT/'outputs/cavern_paper_v02/overleaf_draft.zip'
    extracted=OUT/'overleaf_zip_compile'
    if extracted.exists():raise FileExistsError('ZIP check already exists; preserve the original receipt')
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        if any('provenance' in n or 'real_source' in n or n.endswith('.json') for n in names):raise ValueError('Private metadata in source ZIP')
        for name in names:
            if not (extracted/name).resolve().is_relative_to(extracted.resolve()):raise ValueError('Unsafe ZIP path')
        z.extractall(extracted)
    commands=[['pdflatex','-interaction=nonstopmode','-halt-on-error','main.tex'],['bibtex','main'],
              ['pdflatex','-interaction=nonstopmode','-halt-on-error','main.tex'],
              ['pdflatex','-interaction=nonstopmode','-halt-on-error','main.tex']]
    for i,cmd in enumerate(commands):
        result=subprocess.run(cmd,cwd=extracted,capture_output=True)
        (extracted/f'compile_{i}.log').write_bytes(result.stdout+result.stderr)
        if result.returncode:raise ValueError('Source-only ZIP failed compilation')
    log=(extracted/'main.log').read_text(errors='replace')
    if 'Overfull' in log or 'undefined' in log:raise ValueError('ZIP compile layout/reference warning')
    preview=OUT/'paper_preview_final';preview.mkdir()
    result=subprocess.run(['pdftoppm','-r','100','-png',str(ROOT/'overleaf/build/main.pdf'),str(preview/'page')],capture_output=True)
    if result.returncode:raise ValueError('PDF preview rendering failed')
    qa=subprocess.run([sys.executable,str(ROOT/'scripts/check_cavern_paper.py')],cwd=ROOT,capture_output=True,text=True,check=True)
    paper=json.loads(qa.stdout)
    (preview/'provenance.json').write_text(json.dumps({'pdf_sha256':sha(ROOT/'overleaf/build/main.pdf'),
        'command':'pdftoppm -r 100 -png overleaf/build/main.pdf outputs/cavern_round_v02/paper_preview_final/page',
        'pages':{p.name:sha(p) for p in sorted(preview.glob('page-*.png'))}},indent=2))
    from check_c2_release_v02 import check
    release=check(ROOT/'exports/cavern_pretraining_v02')
    tests=ET.parse(OUT/'tests.xml').getroot()
    report={'status':'PASS','checked_claim_artifacts':len(checked),'gallery_local_links':len(links),
        'canonical_c1_attempts':len(raw),'canonical_c1_accepted':sum(r['accepted'] for r in raw),
        'zip_compiled':True,'zip_files':len(names),'zip_sha256':sha(archive),'paper':paper,
        'release':release,'pytest_suites':[dict(t.attrib) for t in tests.iter('testsuite')],
        'scope':'Integrity and build checks; remaining policy/real-source claims stay pending.'}
    (OUT/'final_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
