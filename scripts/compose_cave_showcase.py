"""Compose actual registered Blender views and a mesh-sampled plan map.

Outputs a 6000 px paper figure, PDF, map and offline interactive HTML.
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import ConnectionPatch, Polygon
import numpy as np
from PIL import Image
import trimesh


BG = '#070b0e'
FG = '#f2f3f1'
GOLD = '#f0b84b'
TEAL = '#55a9ab'
RED = '#ef695d'
ANGLE = np.deg2rad(15.)
ROT = np.array([[np.cos(ANGLE), -np.sin(ANGLE)], [np.sin(ANGLE), np.cos(ANGLE)]])


def compose(folder):
    folder = Path(folder).resolve()
    out = folder / 'figures'
    out.mkdir(exist_ok=True)
    meta = json.loads((folder / 'views/render_metadata.json').read_text())
    views = meta['views']
    report = json.loads((folder / 'validation.json').read_text())
    assets = json.loads((folder / 'assets/manifest.json').read_text())['assets']
    routes = [np.array(r['points']) for r in json.loads((folder / 'scene/navigation/centerline.json').read_text())['routes']]
    path = np.array(json.loads((folder / 'scene/navigation/portal_path.json').read_text())['points'])
    portal = json.loads((folder / 'scene/metadata/portal_validation.json').read_text())
    data = np.load(folder / 'scene/visual/mesh.npz')
    mesh = trimesh.Trimesh(data['vertices'], data['faces'], process=False)
    points, face_ids = trimesh.sample.sample_surface(mesh, 450000, seed=20260908)
    # Restrict to side-facing triangles to make passage outlines readable.
    keep = np.abs(mesh.face_normals[face_ids, 2]) < .72
    points = points[keep]
    xy = points[:, :2] @ ROT.T
    bounds = np.array([xy.min(0), xy.max(0)])
    low, high = bounds[0] - [5, 5], bounds[1] + [5, 5]
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 22,
                         'pdf.fonttype': 42, 'svg.fonttype': 'none'})

    def map_on(ax, markers=True):
        ax.set_facecolor(BG)
        ax.scatter(xy[:, 0], xy[:, 1], s=.12, c='#c3c9ca', alpha=.36, linewidths=0,
                   rasterized=True, zorder=1)
        for r in routes:
            q = r[:, :2] @ ROT.T
            ax.plot(q[:, 0], q[:, 1], color=TEAL, lw=1.1, ls=(0, (3, 3)), zorder=2)
        q = path[:, :2] @ ROT.T
        ax.plot(q[:, 0], q[:, 1], color=GOLD, lw=1.8, zorder=3)
        for p in portal['portals']:
            q = np.array(p['center'])[:2] @ ROT.T
            ax.scatter(*q, marker='s', s=55, facecolor=BG, edgecolor='#9ed9b2', lw=1.5, zorder=5)
            dx, dy = (-1, -4) if p['name'] == 'entrance' else (0, -4)
            ax.text(q[0]+dx, q[1]+dy, p['name'].title(), color='#9ed9b2', ha='center', fontsize=17)
        if markers:
            for view in views:
                q = np.array(view['position'])[:2] @ ROT.T
                t = np.array(view['target'])[:2] @ ROT.T - q
                t /= np.linalg.norm(t)
                perp = np.array([-t[1], t[0]])
                ax.add_patch(Polygon([q + t*2.6, q + perp*.9, q-perp*.9], facecolor=RED, alpha=.65, zorder=4))
                ax.scatter(*q, s=300, facecolor=RED, edgecolor=BG, lw=1.2, zorder=6)
                ax.text(*q, str(view['id']), ha='center', va='center', color='white', fontsize=19,
                        fontweight='bold', zorder=7)
        x, y = low + [9, 3]
        ax.plot([x, x+10], [y, y], color=FG, lw=2)
        ax.plot([x, x], [y-.55, y+.55], color=FG, lw=1.5)
        ax.plot([x+10, x+10], [y-.55, y+.55], color=FG, lw=1.5)
        ax.text(x+5, y+1.2, '10 m', color=FG, fontsize=17, ha='center')
        ax.set(xlim=(low[0], high[0]), ylim=(low[1], high[1]), aspect='equal')
        ax.axis('off')

    fig = plt.figure(figsize=(20, 12), facecolor=BG)
    ax = fig.add_axes([.022, .286, .956, .418])
    map_on(ax)
    # Number order follows camera locations from left to right within each row.
    fig.canvas.draw()
    for k, view in enumerate(views):
        col, top = k % 4, k < 4
        x, y, w, h = .012 + col*.247, .738 if top else .012, .235, .245
        panel = fig.add_axes([x, y, w, h])
        with Image.open(folder / view['image']) as im:
            panel.imshow(im)
        panel.set_axis_off()
        panel.text(.023, .035, f"{view['id']:02d}  {view['title']}", color='white',
                   fontsize=21, fontweight='medium', transform=panel.transAxes,
                   bbox=dict(facecolor=BG, alpha=.8, edgecolor='none', pad=5))
        q = np.array(view['position'])[:2] @ ROT.T
        end = (x + w*.5, y if top else y+h)
        fig.add_artist(ConnectionPatch(xyA=q, coordsA=ax.transData, xyB=end,
            coordsB=fig.transFigure, color='#b7c2c4', linewidth=.9, alpha=.7, zorder=2))
    # Compact legend outside the map; all labels remain readable at two-column width.
    fig.text(.025, .716, 'DOUBLE-LOOP CAVE', color=FG, fontsize=24, weight='bold')
    fig.text(.978, .716, '256 m of designed routes  /  8 registered viewpoints',
             color='#b4bfc3', fontsize=20, ha='right')
    fig.text(.026, .271, 'Gold: verified portal path', color=GOLD, fontsize=20)
    fig.text(.336, .271, 'Teal dashed: construction routes', color=TEAL, fontsize=20)
    fig.text(.978, .271, 'Synthetic mesh-sampled map', color='#bdc5c9', fontsize=20, ha='right')
    fig.savefig(out / 'cave_showcase.png', dpi=300, facecolor=BG)
    fig.savefig(out / 'cave_showcase.pdf', dpi=300, facecolor=BG)
    plt.close(fig)

    # Standalone map with exactly registered clickable camera positions.
    fig = plt.figure(figsize=(16, 6), facecolor=BG)
    ax = fig.add_axes([.012, .012, .976, .976])
    map_on(ax, markers=False)
    fig.canvas.draw()
    width, height = fig.canvas.get_width_height()
    for view in views:
        q = np.array(view['position'])[:2] @ ROT.T
        screen = ax.transData.transform(q)
        view['map_percent'] = [float(screen[0]/width*100), float(100-screen[1]/height*100)]
    fig.savefig(out / 'map.png', dpi=160, facecolor=BG)
    plt.close(fig)
    pose = dict(views=views, map_rotation_degrees=15, map_projection='orthographic XY in meters',
                map_source='Uniform samples of visual triangles with abs(normal.z) < 0.72',
                sampled_points=len(points), ground_truth='Known generated geometry; not LiDAR or SLAM')
    (folder / 'views/registered_views.json').write_text(json.dumps(pose, indent=2), encoding='utf-8')
    create_html(folder, views, report)
    caption = (
        'Qualitative overview of an existing Cave Composer double-loop scene. '
        'Eight numbered images are Cycles renders of the same textured mesh with an intact ceiling '
        'and two actual terminal openings; leaders identify the corresponding camera centers in '
        'an orthographic plan map rotated by 15 degrees. The gray map consists of samples from '
        'side-facing mesh triangles, not LiDAR observations or a SLAM reconstruction. '
        'The gold line is the original independently searched interior A* path with checked terminal '
        'connectors and straight exterior approaches; dashed teal curves are construction routes. '
        f"The derivative contains {report['rock_count']} floor stones and three freestanding checkerboard props. "
        'After asset insertion, distance checks on both the visual and collision scene geometries '
        f"give a minimum continuous path-clearance lower bound of {report['combined_mesh_path']['visual']['continuous_clearance_lower_bound']:.2f} m "
        f"for a required spherical radius of {report['required_radius']:.2f} m. "
        'These checks concern the displayed portal path, not arbitrary robot trajectories. '
        'Images use procedural limestone and neutral inspection lighting without a water medium; '
        'they illustrate generated scene structure and appearance, not a robot-navigation experiment.')
    (out / 'caption.txt').write_text(caption + '\n', encoding='utf-8')
    (out / 'latex_include.tex').write_text('\\begin{figure*}[t]\n  \\centering\n'
        '  \\includegraphics[width=\\textwidth]{figures/cave_showcase.pdf}\n'
        '  \\caption{' + caption + '}\n  \\label{fig:cave-showcase}\n\\end{figure*}\n', encoding='utf-8')
    print('Figure, PDF, registered map, HTML and caption saved:', folder)


def create_html(folder, views, report):
    payload = json.dumps(views, ensure_ascii=False).replace('</', '<\\/')
    html = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Cave Composer · 双回环洞穴探索</title>
<style>
:root{color-scheme:dark;font-family:Inter,"Segoe UI","Microsoft YaHei",sans-serif;background:#090e12;color:#eef2f3}
*{box-sizing:border-box}body{margin:0}main{max-width:1540px;margin:auto;padding:32px}
header{display:flex;justify-content:space-between;align-items:end;gap:30px;margin-bottom:24px}
.eyebrow{font-size:12px;letter-spacing:3px;color:#70b8b8}h1{font-size:32px;font-weight:550;margin:10px 0}
p{color:#9cabb3;line-height:1.7;margin:6px 0}a{color:#c5d8dd;text-decoration:none}a:hover{text-decoration:underline}
.downloads{display:flex;gap:10px;flex-wrap:wrap}.downloads a,button{border:1px solid #34424b;background:#142029;border-radius:6px;padding:10px 15px;color:#e9eeee;cursor:pointer}
.workspace{display:grid;grid-template-columns:1.03fr 1fr;gap:20px;align-items:start}.card{border:1px solid #26323a;border-radius:10px;overflow:hidden;background:#0d151b}
.bar{padding:15px 18px;border-bottom:1px solid #26323a;display:flex;justify-content:space-between;align-items:center;gap:10px;font-size:14px}
#map{position:relative;background:#070b0e}#map img{display:block;width:100%;height:auto}
.pin{position:absolute;transform:translate(-50%,-50%);padding:0;width:27px;height:27px;border-radius:50%;background:#b34b42;border:2px solid #080d11;color:white;font-size:13px;font-weight:700;z-index:2}
.pin.active{background:#fcab67;outline:3px solid #f8e3b36b;color:#201b15}.pin:hover{scale:1.15}
.legend{padding:13px 18px;color:#9baeb7;font-size:12px;line-height:1.8}.gold{color:#f0b84b}.teal{color:#55a9ab}
#hero{display:block;width:100%;aspect-ratio:1.6;object-fit:contain;background:#050809;cursor:zoom-in}
.detail{padding:16px 18px}.detail h2{margin:0 0 8px;font-size:21px;font-weight:500}#pose{font-family:monospace;color:#899da9;font-size:12px;line-height:1.7}
.thumbs{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:18px}.thumb{padding:0;overflow:hidden;background:#0d151b;text-align:left;border:1px solid #293641;transition:border .2s}
.thumb.active{border-color:#eea66c}.thumb img{display:block;width:100%;aspect-ratio:1.6}.thumb span{display:block;padding:9px;font-size:12px}
.facts{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:25px 0}.fact{border-top:1px solid #33434c;padding-top:15px}.fact strong{font-size:26px;font-weight:450;color:#dbe6e9}.fact p{font-size:13px}
details{margin-top:24px;padding:18px 0;border-top:1px solid #293640}summary{cursor:pointer;color:#cfdbdf}details p{max-width:1050px;font-size:14px;margin-top:14px}.plate{width:100%;display:block;border:1px solid #27343c;margin-top:20px}footer{font-size:12px;color:#7f939f;padding:25px 0}
dialog{border:1px solid #486070;padding:0;max-width:95vw;max-height:95vh;background:#0b1116}dialog::backdrop{background:#000d}dialog img{display:block;max-width:92vw;max-height:86vh}dialog button{position:absolute;top:10px;right:10px}
@media(max-width:960px){main{padding:18px}.workspace{grid-template-columns:1fr}header{display:block}.downloads{margin-top:18px}.facts{grid-template-columns:repeat(2,1fr)}h1{font-size:26px}}
</style><main><header><div><div class="eyebrow">CAVE COMPOSER / SCENE EXPLORER</div><h1>走进一个双回环洞穴</h1>
<p>点击地图上的编号，查看同一位置的洞内渲染。方向、尺度与场景坐标一一对应。</p></div>
<nav class="downloads"><a href="figures/cave_showcase.pdf">论文 PDF</a><a href="figures/cave_showcase.png">高清 PNG</a><a href="cave_showcase.blend">Blender 场景</a></nav></header>
<div class="workspace"><section class="card"><div class="bar"><span>全局结构 · 俯视</span><span>单位 m / 旋转 15°</span></div><div id="map"><img src="figures/map.png" alt="从实际网格采样的洞穴全局地图"></div>
<div class="legend"><span class="gold">━ 已验证贯穿路径</span> &nbsp; <span class="teal">┄ 构建路线</span><br>灰色点由模型表面采样得到；不是激光雷达或 SLAM 重建。</div></section>
<section class="card"><div class="bar"><span id="counter"></span><div><button id="previous" aria-label="上一个视点">←</button> <button id="next" aria-label="下一个视点">→</button></div></div>
<img id="hero" alt="当前洞内视点"><div class="detail"><h2 id="viewtitle"></h2><div id="pose"></div></div></section></div>
<div class="thumbs" id="thumbs"></div>
<section class="facts"><div class="fact"><strong>256 m</strong><p>构建路线总长 · 两个回环</p></div><div class="fact"><strong>100 + 3</strong><p>落石资产 + 棋盘标定板道具</p></div><div class="fact"><strong>0.81 m</strong><p>加入资产后的路径净空下界</p></div><div class="fact"><strong>2 个</strong><p>实际入口 / 出口 · 完整洞顶</p></div></section>
<details><summary>场景说明与验证范围</summary><p>复用 v0.3 的 ood_topology / scene_000001，未重新生成洞穴布局。石块贴靠洞底，三块棋盘板放在通道侧面。资产包含显式碰撞几何，所有构建路线均用保守包围球排除资产侵入，加入资产后的 visual / collision 网格也重新检查了原有贯穿路径。机器人半径 0.35 m，安全余量 0.20 m，要求总半径 0.55 m。</p>
<p>画面是 Blender Cycles 对真实生成模型的渲染，使用程序化石灰岩材质和检查照明，未模拟水体。编号表示相机位置，不代表机器人已经执行的轨迹；棋盘板是可见场景道具，不是完成了相机标定实验。金线在洞内来自独立 A*，终端连接和洞外直线段经过单独检查。</p>
<p><a href="validation.json">查看几何验证报告</a> · <a href="assets/manifest.json">资产清单</a> · <a href="views/registered_views.json">相机与地图坐标</a> · <a href="figures/caption.txt">论文图注</a></p></details>
<a href="figures/cave_showcase.png"><img class="plate" src="figures/cave_showcase.png" alt="论文用全局地图与八个关联视点"></a>
<footer>本页可直接离线打开。独立 A* 路径 / 相机坐标 / 资产碰撞检查均可追溯至原始场景文件。</footer>
<dialog id="viewer"><button id="close">关闭 ×</button><img id="full" alt="全分辨率洞内图"></dialog></main>
<script>const views=__VIEWS__;let current=0;const $=s=>document.querySelector(s);
views.forEach((v,i)=>{const p=document.createElement('button');p.className='pin';p.textContent=v.id;p.title=v.title;p.setAttribute('aria-label',`视点 ${v.id}: ${v.title}`);p.style.left=v.map_percent[0]+'%';p.style.top=v.map_percent[1]+'%';p.onclick=()=>select(i);$('#map').append(p);
const t=document.createElement('button');t.className='thumb';const im=document.createElement('img');im.src=v.image;im.alt=v.title;const s=document.createElement('span');s.textContent=String(v.id).padStart(2,'0')+' · '+v.title;t.append(im,s);t.onclick=()=>select(i);$('#thumbs').append(t);});
function select(i){current=(i+views.length)%views.length;const v=views[current];$('#hero').src=v.image;$('#hero').alt=v.title;$('#viewtitle').textContent=v.title;$('#counter').textContent=`视点 ${v.id} / 8`;$('#pose').textContent=`${v.route} · XYZ (${v.position.map(x=>x.toFixed(2)).join(', ')}) m · 19 mm / 36 mm sensor`;
document.querySelectorAll('.pin').forEach((x,k)=>x.classList.toggle('active',k===current));document.querySelectorAll('.thumb').forEach((x,k)=>x.classList.toggle('active',k===current));}
$('#previous').onclick=()=>select(current-1);$('#next').onclick=()=>select(current+1);$('#hero').onclick=()=>{$('#full').src=views[current].image;$('#viewer').showModal();};$('#close').onclick=()=>$('#viewer').close();document.addEventListener('keydown',e=>{if(e.key==='ArrowRight')select(current+1);if(e.key==='ArrowLeft')select(current-1);});select(0);
</script></html>'''
    html = html.replace('__VIEWS__', payload).replace('100 + 3', f"{report['rock_count']} + {report['board_count']}")
    clearance = min(x['continuous_clearance_lower_bound'] for x in report['combined_mesh_path'].values())
    html = html.replace('0.81 m', f'{clearance:.2f} m')
    (folder / 'index.html').write_text(html, encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', default='outputs/cave_showcase_v01')
    compose(parser.parse_args().folder)
