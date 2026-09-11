"""Draft QA and a fail-closed submission gate. Human decisions stay human."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

def submission_blockers(text, claims, approvals):
    blockers = []
    if re.search(r'TODO|UNCONFIRMED|\\missing\b', text):
        blockers.append('unresolved_text_or_result_placeholders')
    for claim in claims['claims']:
        if claim.get('required_for_submission') and claim['status'] in ['not_run', 'blocked', 'training_reported_by_collaborator']:
            blockers.append('evidence_pending:' + claim['id'])
    for field in ['technical_content_reviewed', 'author_identity_reviewed', 'anonymity_reviewed',
                  'licenses_reviewed', 'ai_disclosure_reviewed', 'claim_evidence_reviewed', 'final_submission_authorized']:
        if approvals.get(field) is not True:
            blockers.append('human_review_pending:' + field)
    return blockers

def check(submission=False):
    paper = ROOT / 'overleaf'; build = paper / 'build'; pdf = build / 'main.pdf'
    def run(*args):
        return subprocess.check_output(args).decode('utf-8', errors='replace')
    info = run('pdfinfo', str(pdf)); fonts = run('pdffonts', str(pdf))
    text = run('pdftotext', '-layout', str(pdf), '-')
    pages = int(re.search(r'Pages:\s+(\d+)', info).group(1))
    font_rows = [x for x in fonts.splitlines()[2:] if x.strip()]
    embedded = bool(font_rows) and all(re.search(r'\byes\s+(yes|no)\s+(yes|no)\s+\d+\s+\d+\s*$', x) for x in font_rows)
    log = (build / 'main.log').read_text(errors='replace')
    sources = [paper/'main.tex', *sorted((paper/'sections').glob('*.tex')), *sorted((paper/'tables').glob('*.tex'))]
    source_text = '\n'.join(p.read_text(encoding='utf-8') for p in sources)
    identity_tokens = ['michaelgents', 'Administrator', 'D:\\Desktop', 'Qixingyan', 'Zhaoqing']
    problems = []
    if pages > 8: problems.append('over_8_total_pages')
    if '612 x 792' not in info: problems.append('not_us_letter')
    if not embedded or 'Type 3' in fonts: problems.append('font_embedding_or_type3')
    if 'undefined references' in log or re.search(r'Citation .* undefined', log): problems.append('unresolved_references')
    if re.search(r'Overfull \\[hv]box', log): problems.append('overfull_boxes')
    if any(t.lower() in (text+info).lower() for t in identity_tokens): problems.append('identity_token_detected')
    if re.search(r'^Author:[ \t]*[^\s]', info, re.M): problems.append('pdf_author_metadata')
    claims = yaml.safe_load((paper/'CLAIM_EVIDENCE.yaml').read_text(encoding='utf-8'))
    approvals = json.loads((ROOT/'research_workspace/submission_approvals.json').read_text())
    blockers = submission_blockers(source_text, claims, approvals)
    report = {'status':'draft_checked' if not problems else 'draft_issues', 'pages_including_references':pages,
              'all_fonts_embedded':bool(embedded), 'draft_problems':problems,
              'submission_ready':not (problems or blockers), 'submission_blockers':blockers,
              'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),
              'limitation':'Static checks cannot establish truthful results or complete anonymity; human review is required.'}
    (build/'paper_check.json').write_text(json.dumps(report,indent=2)+'\n')
    (build/'pdfinfo.txt').write_text(info,encoding='utf-8'); (build/'pdffonts.txt').write_text(fonts,encoding='utf-8')
    (build/'main.txt').write_text(text,encoding='utf-8')
    print(json.dumps(report,indent=2))
    return 1 if problems or (submission and blockers) else 0

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--submission',action='store_true')
    raise SystemExit(check(parser.parse_args().submission))
