"""Measured dataset summaries, CSV and a local visual index for every outcome."""
import csv
from collections import Counter
import html
import json
from pathlib import Path
import numpy as np
from .bundle import atomic_json


MEASURES=['total_length','num_turns','branch_count','chamber_count','vertical_range',
          'minimum_width','minimum_mesh_clearance','mean_forward_visibility',
          'visual_triangles','collision_triangles','generation_seconds']


def write_dataset_report(root,manifest):
    root=Path(root)
    valid=[r for r in manifest['records'] if r['status']=='VALID']
    stats={}
    for metric in MEASURES:
        values=[r['metrics'][metric] for r in valid if metric in r.get('metrics',{})]
        if values:
            stats[metric]={'count':len(values),'min':float(np.min(values)),
                           'median':float(np.median(values)),'p95':float(np.quantile(values,.95)),
                           'max':float(np.max(values))}
    failures=Counter()
    for record in manifest['records']:
        if record['status'] in ('INVALID','ERROR'):
            failures.update(record.get('failed_checks') or [record.get('failed_stage','generation_error')])
    summary={'schema_version':1,'status':manifest['status'],'split':manifest['distribution']['split'],
             'requested':manifest['requested'],'valid':manifest['valid'],'invalid':manifest['invalid'],
             'pending':manifest['pending'],'metrics_for_valid_scenes':stats,'failure_reasons':dict(failures),
             'latest_run':manifest['runs'][-1],
             'scope':'offline generation and geometry checks; timings are observed, not controlled benchmarks'}
    atomic_json(root/'quality.json',summary)
    fields=['index','seed','status','attempts','path',*MEASURES,'error','failed_checks']
    with (root/'metrics.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields)
        writer.writeheader()
        for record in manifest['records']:
            row={key:record.get(key,'') for key in fields}
            row.update({k:v for k,v in record.get('metrics',{}).items() if k in MEASURES})
            row['failed_checks']='; '.join(record.get('failed_checks',[]))
            writer.writerow(row)
    cards=[]
    for record in manifest['records']:
        path=record['path']
        folder=root/path
        previews={name:f'{path}/previews/{name}.png' for name in ['overview','inside_01','inside_02','topology']
                  if (folder/'previews'/f'{name}.png').exists()}
        links=[]
        for label,rel in [('config','metadata/config.yaml'),('validation','metadata/validation.json'),
                          ('stages','metadata/run.json'),('Blender','cave.blend')]:
            if (folder/rel).exists():
                links.append(f'<a href="{path}/{rel}">{label}</a>')
        image=''
        if previews:
            initial=previews.get('overview',previews.get('topology',next(iter(previews.values()))))
            encoded=html.escape(json.dumps(previews),quote=True)
            image=f'<a class="preview" href="{initial}"><img data-previews="{encoded}" src="{initial}" loading="lazy" alt="{path}"></a>'
        metrics=record.get('metrics',{})
        details=f"{metrics.get('total_length',0):.1f} m · {metrics.get('num_turns',0)} turns · {metrics.get('branch_count',0)} branches" if metrics else ''
        error=html.escape(record.get('error',''))
        if record.get('failed_checks'):
            error+=' '+html.escape(', '.join(record['failed_checks']))
        diagnostic=record.get('diagnostics')
        if diagnostic and (root/diagnostic/'metadata/run.json').is_file():
            links.append(f'<a href="{html.escape(diagnostic)}/metadata/run.json">failure log</a>')
        cards.append(f'<article data-status="{record["status"]}"><h2>{path} <small>{record["status"]}</small></h2><p>seed {record["seed"]} · attempt {record["attempts"]}</p>{image}<p>{details}</p><p class="error">{error}</p><nav>{" · ".join(links)}</nav></article>')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Cave dataset quality</title>
<style>:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#101b22;color:#e8f0f3}body{max-width:1450px;margin:32px auto;padding:0 20px}h1{font-size:36px}h2{font-size:18px}small{font-size:12px;color:#a6dbc9}a{color:#8bd7c8}p{color:#b5c6d0;line-height:1.6}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:20px}article{background:#1b2a33;border:1px solid #344a57;border-radius:10px;padding:18px;min-width:0}img{width:100%;aspect-ratio:1.6;object-fit:contain;background:#111c23;border-radius:6px}.error{color:#ffb4a7;overflow-wrap:anywhere}nav{font-size:13px}.controls{display:flex;gap:16px;flex-wrap:wrap;margin:24px 0}select{font:inherit;padding:8px;background:#263e4b;color:inherit;border:1px solid #496a79;border-radius:5px}[hidden]{display:none!important}@media(max-width:380px){.grid{grid-template-columns:1fr}}</style>
<body><h1>Cave dataset / '''+html.escape(summary['split'])+'''</h1><p>'''+f"{summary['valid']} VALID · {summary['invalid']} failed · {summary['pending']} pending / {summary['requested']} requested · {summary['status']}"+'''</p>
<p><a href="manifest.json">Manifest / resume contract</a> · <a href="quality.json">Quality summary</a> · <a href="metrics.csv">Metrics CSV</a></p>
<p>Geometry, material and previews from the automated pipeline. Counts include every requested seed; failed scenes are retained. Widths are measured samples. VALID refers to offline geometry and spherical-robot path checks.</p>
<div class="controls"><label>Outcome <select id="status"><option value="all">All scenes</option><option value="VALID">Valid</option><option value="failed">Failed / pending</option></select></label><label>View <select id="view"><option value="overview">Overview</option><option value="inside_01">Inside 1</option><option value="inside_02">Inside 2</option><option value="topology">Topology</option></select></label></div>
<div class="grid">'''+''.join(cards)+'''</div><script>
document.getElementById('status').addEventListener('change',e=>document.querySelectorAll('article').forEach(a=>a.hidden=e.target.value!=='all'&&(e.target.value==='VALID'?a.dataset.status!=='VALID':a.dataset.status==='VALID')));
document.getElementById('view').addEventListener('change',e=>document.querySelectorAll('img[data-previews]').forEach(img=>{const p=JSON.parse(img.dataset.previews);const src=p[e.target.value]||p.topology||Object.values(p)[0];img.src=src;img.parentElement.href=src;}));
</script></body></html>'''
    (root/'index.html').write_text(page,encoding='utf-8')
    return summary
