"""Create a new source-only Overleaf import ZIP, excluding private evidence."""
import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def package(output):
    output=Path(output);paper=ROOT/'overleaf'
    files=[paper/n for n in ['main.tex','ieeeconf.cls','IEEEtran.bst','refs.bib']]
    for pattern in ['sections/*.tex','tables/*.tex']:
        files.extend(sorted(paper.glob(pattern)))
    # Resolve only manuscript-used figures. Private unused source preparations
    # and local receipts must never enter an anonymous source ZIP implicitly.
    for source in tuple(files):
        if source.suffix!='.tex':continue
        for ref in re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}',source.read_text(encoding='utf-8')):
            figure=(paper/ref).resolve()
            if not figure.suffix:figure=figure.with_suffix('.pdf')
            if not figure.is_relative_to(paper.resolve()) or not figure.is_file():
                raise ValueError('Missing or out-of-paper figure: '+ref)
            files.append(figure)
            if figure.with_suffix('.svg').exists():files.append(figure.with_suffix('.svg'))
    files=sorted(set(p.resolve() for p in files))
    if output.exists():raise FileExistsError('Use a new draft ZIP version')
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for p in files:archive.write(p,p.relative_to(paper).as_posix())
        archive.writestr('IMPORT.txt','Working draft, not submission-ready. Compile main.tex with pdfLaTeX and BibTeX. C1 contains a six-request descriptive pilot after a declared OBJ seam recheck. PLUME comparison, navigation policy results and real transfer remain unavailable. Only manuscript-used figures are included. Keep source assets, private reviews and evidence audit in the local repository.\n')
    print(json.dumps({'zip':str(output),'files':len(files)+1,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'purpose':'private Overleaf draft import'},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);package(p.parse_args().output)
