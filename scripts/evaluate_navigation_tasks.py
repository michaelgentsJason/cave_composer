"""Audit task packs and build a directly inspectable offline task gallery."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cave_composer.bundle import atomic_json, file_sha256, verify_bundle
from cave_composer.planning import certify_polyline
from cave_composer.reference_data import cross_section_statistics
from cave_composer.tasks import load_task_pack


def evaluate(packs, output):
    output = Path(output)
    if output.exists():
        raise ValueError('Use a new evaluation directory')
    records, display = [], []
    for path in packs:
        folder = Path(path).resolve()
        contract, episodes = load_task_pack(folder)
        manifest = json.loads((folder/'metadata/manifest.json').read_text())
        routes = json.loads((folder/'navigation/centerline.json').read_text())['routes']
        meshes = {}
        for kind in ['visual', 'collision']:
            d = np.load(folder/kind/'mesh.npz')
            meshes[kind] = trimesh.Trimesh(d['vertices'], d['faces'], process=False)
            assert file_sha256(folder/kind/'mesh.npz') == manifest['source_mesh_files'][kind]
        tasks = []
        for r in manifest['all_requests']:
            t = json.loads((folder/'tasks'/f"{r['id']}.json").read_text())
            if t['planning']['status'] == 'PASS':
                for kind, mesh in meshes.items():
                    certificate = certify_polyline(mesh, t['planning']['points'],
                        contract['robot_envelope']['radius']+contract['robot_envelope']['margin'])
                    if certificate['status'] != 'PASS':
                        raise ValueError('Independent final-geometry recheck failed')
            tasks.append(t)
        metrics = [r['metrics'] for r in manifest['all_requests'] if r['metrics']]
        off_main = sum(t['request']['goal_route'] != 'main' for t in tasks if t['planning']['status'] == 'PASS')
        spec = json.loads((folder/'metadata/config.json').read_text())
        junction_positions = [r['points'][0] for r in routes[1:]]
        junction_positions += [r['points'][-1] for r, b in zip(routes[1:], spec['branches']) if 'rejoin_at' in b]
        shape = cross_section_statistics(meshes['visual'], np.asarray(routes[0]['points'])[::8], junction_positions)
        summary = {'scene': folder.name, 'source_name': manifest['source_name'], 'source_split': manifest['source_split'],
                   'requested': manifest['requested'], 'passed': manifest['passed'], 'failed': manifest['failed'],
                   'endpoint_classes': dict(Counter(t['request']['requested_class'] for t in tasks)),
                   'goals_in_branch_interiors': off_main,
                   'geometric_bins': dict(Counter(m['geometric_bin'] for m in metrics)),
                   'path_length_range_m': [min(m['path_length_m'] for m in metrics), max(m['path_length_m'] for m in metrics)] if metrics else None,
                   'minimum_clearance_lower_bound_m': min(m['continuous_clearance_lower_bound_m'] for m in metrics) if metrics else None,
                   'cross_section_profile': shape, 'semantic_digest': manifest['semantic_digest'],
                   'independent_dual_mesh_recheck': 'PASS', 'pack_checksums_sha256': file_sha256(folder/'metadata/checksums.json')}
        records.append(summary)
        display.append({'name': folder.name, 'routes': routes, 'tasks': tasks, 'summary': summary})
    output.mkdir(parents=True)
    result = {'status': 'PASS', 'scenes': records, 'total_requested': sum(r['requested'] for r in records),
              'total_passed': sum(r['passed'] for r in records),
              'unit_of_independent_scene_sampling': len(records),
              'scope': 'Engineering task-pack validation on selected existing scenes; task successes are correlated within caves. No learned policy or PLUME performance comparison.'}
    atomic_json(output/'evaluation.json', result)
    template = r'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Cave Composer · 多任务验证</title>
<style>body{font:16px "Segoe UI","Microsoft YaHei",sans-serif;background:#101820;color:#dce8ed;margin:30px auto;padding:0 24px;max-width:1250px}h1{font-weight:550}p{line-height:1.7;color:#adc0ca}select{background:#22323f;color:white;border:1px solid #456;padding:10px;margin:8px}svg{width:100%;height:480px;background:#091117;border:1px solid #344754;border-radius:8px}table{width:100%;border-collapse:collapse}td,th{padding:10px;border-bottom:1px solid #344754;text-align:left}#details{white-space:pre-wrap;font-family:monospace;line-height:1.8}a{color:#72c7ce}.legend{color:#a6becb}.good{color:#77d8ad}</style>
<h1>多任务导航 · 生成结构进入实际任务</h1><p>同一个洞穴，独立选择分支内目标、分支返回与跨分支任务。每个请求均保留，路径重新搜索并在两套最终网格上检查。</p>
<label>洞穴 <select id="scene"></select></label><label>任务 <select id="task"></select></label>
<svg id="map" viewBox="0 0 1100 480" role="img" aria-label="任务路径与洞穴构建路线"></svg>
<p class="legend">灰色：构建路线　洋红：独立搜索路径　绿色 S：起点　橙色 G：目标。XY 俯视，沿比例显示；并非 SLAM 地图。</p>
<div id="details"></div><h2>验收汇总</h2><table id="summary"><thead><tr><th>场景</th><th>请求 / 通过</th><th>分支内目标</th><th>路径长度</th><th>净空下界</th></tr></thead><tbody></tbody></table>
<p>要求半径 0.55 m。难度标签为预先定义的几何分层，尚未按策略成功率校准。这里的成功指几何验证通过。三个洞穴中的任务不视为独立同分布样本。目标如何传递给仅使用双目 RGB 的策略仍需定义。</p>
<p><a href="evaluation.json">原始验收记录</a></p><script>const data=__DATA__;const $=s=>document.querySelector(s);const svg=$('#map');
data.forEach((s,i)=>{$('#scene').add(new Option(s.name,i));const tr=document.createElement('tr');const r=s.summary;[s.name,r.requested+' / '+r.passed,r.goals_in_branch_interiors,r.path_length_range_m.map(x=>x.toFixed(1)).join('–')+' m',r.minimum_clearance_lower_bound_m.toFixed(3)+' m'].forEach(v=>{const td=document.createElement('td');td.textContent=v;tr.append(td)});$('#summary tbody').append(tr)});
function choose(){const d=data[$('#scene').value];$('#task').replaceChildren();d.tasks.forEach((t,i)=>$('#task').add(new Option(t.request.id+' · '+t.request.requested_class+' · '+t.planning.status,i)));draw()}
function draw(){const d=data[$('#scene').value],t=d.tasks[$('#task').value],p=d.routes.flatMap(r=>r.points);const xmin=Math.min(...p.map(x=>x[0])),xmax=Math.max(...p.map(x=>x[0])),ymin=Math.min(...p.map(x=>x[1])),ymax=Math.max(...p.map(x=>x[1]));const scale=Math.min(1020/Math.max(xmax-xmin,1),400/Math.max(ymax-ymin,1));const xy=q=>[550+(q[0]-(xmin+xmax)/2)*scale,240-(q[1]-(ymin+ymax)/2)*scale];svg.replaceChildren();
function line(points,color,width){const e=document.createElementNS('http://www.w3.org/2000/svg','polyline');e.setAttribute('points',points.map(x=>xy(x).join(',')).join(' '));e.setAttribute('fill','none');e.setAttribute('stroke',color);e.setAttribute('stroke-width',width);svg.append(e)}d.routes.forEach(r=>line(r.points,'#4b626e',8));if(t.planning.points)line(t.planning.points,'#e783c2',3);
[['start','S','#7ee0ac'],['goal','G','#ffbd78']].forEach(([k,label,color])=>{if(!t.request[k])return;const q=xy(t.request[k]),e=document.createElementNS('http://www.w3.org/2000/svg','circle');e.setAttribute('cx',q[0]);e.setAttribute('cy',q[1]);e.setAttribute('r',8);e.setAttribute('fill',color);svg.append(e);const tx=document.createElementNS('http://www.w3.org/2000/svg','text');tx.setAttribute('x',q[0]+11);tx.setAttribute('y',q[1]-10);tx.setAttribute('fill',color);tx.textContent=label;svg.append(tx)});
const m=t.planning.metrics;$('#details').textContent=t.request.start_route+' → '+t.request.goal_route+'\n'+(m?`路径 ${m.path_length_m.toFixed(2)} m | 净空下界 ${m.continuous_clearance_lower_bound_m.toFixed(3)} m | 几何分层 ${m.geometric_bin}`:t.planning.reason)}$('#scene').onchange=choose;$('#task').onchange=draw;choose();</script></html>'''
    (output/'index.html').write_text(template.replace('__DATA__', json.dumps(display).replace('</', '<\\/')), encoding='utf-8')
    print(json.dumps({'total_requested': result['total_requested'], 'passed': result['total_passed']}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packs', nargs='+', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    evaluate(args.packs, args.output)
