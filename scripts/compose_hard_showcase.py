"""Reference-style scientific plate from registered renders of hard_005."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import ConnectionPatch
import numpy as np
from PIL import Image
from scipy.optimize import linear_sum_assignment
import trimesh


def compose(folder):
    folder=Path(folder).resolve()
    out=folder/'figures';out.mkdir(exist_ok=True)
    metadata=json.loads((folder/'views/render_metadata.json').read_text())
    views=metadata['views']
    source=json.loads((folder/'source.json').read_text())
    report=json.loads((folder/'validation.json').read_text())
    routes=[np.asarray(r['points']) for r in json.loads((folder/'scene/navigation/centerline.json').read_text())['routes']]
    data=np.load(folder/'scene/visual/mesh.npz')
    mesh=trimesh.Trimesh(data['vertices'],data['faces'],process=False)
    points,ids=trimesh.sample.sample_surface(mesh,1200000,seed=1080501)
    points=points[np.abs(mesh.face_normals[ids,2])<.78]
    theta=np.deg2rad(source['map_rotation_degrees'])
    rotation=np.array([[np.cos(theta),-np.sin(theta)],[np.sin(theta),np.cos(theta)]])
    xy=points[:,:2]@rotation.T
    low,high=xy.min(0)-[5,5],xy.max(0)+[5,5]
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':27,'pdf.fonttype':42,'svg.fonttype':'none'})

    def draw_map(ax, markers=True):
        ax.set_facecolor('black')
        ax.scatter(*xy.T,s=.12,c='#c7c7c7',alpha=.40,linewidths=0,rasterized=True)
        for route in routes:
            q=route[:,:2]@rotation.T
            ax.plot(*q.T,color='#ecb017',lw=1.8,zorder=3)
        if markers:
            for v in views:
                q=np.asarray(v['position'])[:2]@rotation.T
                ax.scatter(*q,s=110,color='#ed3032',zorder=8)
                ax.annotate(str(v['id']),q,xytext=(8,8),textcoords='offset points',
                            color='white',fontsize=27,zorder=9)
        ax.set(xlim=(low[0],high[0]),ylim=(low[1],high[1]),aspect='equal')
        ax.axis('off')

    fig=plt.figure(figsize=(24,12),facecolor='black')
    ax=fig.add_axes([.174,.03,.652,.706]);draw_map(ax)
    fig.canvas.draw()
    # Six images across the top, three down each side: same framing principle
    # as the supplied reference. Every image remains an uncropped 4:3 render.
    gap=.003
    slots=[]
    for k in range(6):slots.append((k/6+gap/2,.752,1/6-gap,.244))
    for k in range(3):slots.append((gap/2,.502-k*.25,1/6-gap,.244))
    for k in range(3):slots.append((5/6+gap/2,.502-k*.25,1/6-gap,.244))
    anchors=np.array([[x+w*.5,y+h*.5] for x,y,w,h in slots])
    screen=np.array([fig.transFigure.inverted().transform(ax.transData.transform(np.asarray(v['position'])[:2]@rotation.T)) for v in views])
    _,assignment=linear_sum_assignment(np.sum((screen[:,None,:]-anchors[None,:,:])**2,axis=2))
    for v,slot in zip(views,assignment):
        x,y,w,h=slots[slot]
        panel=fig.add_axes([x,y,w,h],zorder=2)
        with Image.open(folder/v['image']) as im:panel.imshow(im)
        panel.set_axis_off()
        panel.text(.035,.95,str(v['id']),transform=panel.transAxes,ha='left',va='top',
                   color='white',fontsize=28,bbox={'facecolor':'black','alpha':.4,'edgecolor':'none','pad':3})
        q=np.asarray(v['position'])[:2]@rotation.T
        fig.add_artist(ConnectionPatch(xyA=q,coordsA=ax.transData,xyB=(x+w*.5,y+h*.48),
            coordsB=fig.transFigure,color='#b5b5b5',lw=1.05,alpha=.8,zorder=5))
        v['plate_panel']=[x,y,w,h]
        v['plate_map_percent']=(screen[v['id']-1]*[100,-100]+[0,100]).tolist()
    # Orthogonal metric scale, independent of the map's display rotation.
    unit=fig.transFigure.inverted().transform(ax.transData.transform(low+[10,0]))-fig.transFigure.inverted().transform(ax.transData.transform(low))
    origin=np.array([.19,.045]);dx=float(unit[0]);dy=dx*2
    for delta in [[dx,0],[0,dy]]:
        fig.add_artist(ConnectionPatch(xyA=origin,coordsA=fig.transFigure,xyB=origin+delta,
            coordsB=fig.transFigure,color='white',lw=1.5,arrowstyle='->',mutation_scale=18,zorder=10))
    fig.text(origin[0]+dx*.5,origin[1]+.014,'10 m',ha='center',color='white',fontsize=25)
    fig.text(origin[0]-.012,origin[1]+dy*.5,'10 m',va='center',rotation=90,color='white',fontsize=25)
    fig.savefig(out/'cave_showcase.png',dpi=300,facecolor='black')
    fig.savefig(out/'cave_showcase.pdf',dpi=300,facecolor='black')
    plt.close(fig)
    fig=plt.figure(figsize=(16,9),facecolor='black');ax=fig.add_axes([.02,.02,.96,.96])
    draw_map(ax,markers=False);fig.canvas.draw()
    for v in views:
        p=fig.transFigure.inverted().transform(ax.transData.transform(np.asarray(v['position'])[:2]@rotation.T))
        v['map_percent']=[float(p[0]*100),float((1-p[1])*100)]
    fig.savefig(out/'map.png',dpi=180,facecolor='black');plt.close(fig)
    registration={'views':views,'rotation_degrees':source['map_rotation_degrees'],
        'projection':'Orthographic XY in metres','sample_count':len(points),'sampling_seed':1080501,
        'map_source':'Uniform visual-mesh surface samples with abs(normal.z)<0.78; not sensor measurements',
        'yellow_lines':'Construction passage centerlines; not an executed trajectory or independent planner output'}
    (folder/'views/registered_views.json').write_text(json.dumps(registration,indent=2),encoding='utf-8')
    caption=(f"Qualitative overview of Cave Composer's hard_005 environment (seed {source['seed']}). "
        f"The same generated cave contains two bypass loops, two blind branches and {source['total_route_length_m']:.1f} m of designed passages. "
        'Twelve Blender Cycles views are registered to their camera centers (red markers) on an orthographic map. '
        'The gray map is sampled from side-facing mesh triangles; yellow curves denote designed passage centerlines. '
        'Neither the map nor the curves represent a sensor reconstruction or an executed robot trajectory. '
        f"The derivative adds {report['rock_count']} floor stones and {report['board_count']} checkerboard props while retaining the cave roof and two terminal openings. "
        'Images use the source procedural rock material and inspection lighting without a participating water medium. '
        'All views are actual renders of the registered scene, not image-generated illustrations.')
    (out/'caption.txt').write_text(caption+'\n',encoding='utf-8')
    (out/'latex_include.tex').write_text('\\begin{figure*}[t]\n\\centering\n'
        '\\includegraphics[width=\\textwidth]{figures/cave_showcase.pdf}\n'
        '\\caption{'+caption.replace('_','\\_')+'}\n\\label{fig:hard-cave-showcase}\n\\end{figure*}\n',encoding='utf-8')
    write_html(folder,views,source,report)
    print('Composed 7200 x 3600 PNG, PDF, registered map and offline HTML',flush=True)


def write_html(folder,views,source,report):
    payload=json.dumps(views,ensure_ascii=False).replace('</','<\\/')
    html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cave Composer · Hard 005 showcase</title><style>
*{box-sizing:border-box}body{margin:0;background:#080909;color:#eee;font-family:Arial,"Microsoft YaHei",sans-serif}main{max-width:1700px;margin:auto;padding:28px}h1{font-size:28px;font-weight:500}p{color:#aaa;line-height:1.7}a{color:#e8b633}nav{display:flex;gap:24px;flex-wrap:wrap;margin:18px 0}.plate{width:100%;display:block}.work{display:grid;grid-template-columns:1.15fr 1fr;gap:20px;margin-top:26px}#map{position:relative;background:black;align-self:center}#map img{width:100%;display:block}.pin{position:absolute;transform:translate(-50%,-50%);border-radius:50%;background:#e33335;width:25px;height:25px;padding:0;border:1px solid black;color:white;font-weight:bold;cursor:pointer}.pin.active{outline:2px solid #efb923}#hero{width:100%;display:block;cursor:zoom-in}.controls{display:flex;justify-content:space-between;align-items:center;margin-top:10px}button{background:#222;color:white;border:1px solid #555;padding:8px 15px;cursor:pointer}.thumbs{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin-top:24px}.thumb{padding:0}.thumb img{width:100%;display:block}.thumb span{display:block;padding:8px;font-size:12px}.thumb.active{border-color:#e8b633}details{margin-top:25px;color:#aaa;line-height:1.7}#pose{font-family:monospace;font-size:12px}dialog{padding:0;border:1px solid #444;background:#080909;max-width:96vw}dialog::backdrop{background:#000d}dialog img{max-width:92vw;max-height:86vh;display:block}dialog button{position:absolute;right:8px;top:8px}@media(max-width:800px){main{padding:16px}.work{grid-template-columns:1fr}.thumbs{grid-template-columns:repeat(3,1fr)}h1{font-size:23px}}
</style><main><h1>Hard 005 · 双回环与盲支路</h1><p>同一生成洞穴的 12 个内部渲染视点，点击地图编号查看洞内结构与道具。</p>
<nav><a href="figures/cave_showcase.png">7200 px 总览</a><a href="figures/cave_showcase.pdf">论文 PDF</a><a href="figures/caption.txt">英文图注</a><a href="cave_showcase.blend">Blender 场景</a></nav>
<a href="figures/cave_showcase.png"><img class="plate" src="figures/cave_showcase.png" alt="黑底洞穴地图与12个关联内部视点"></a>
<section class="work"><div id="map"><img src="figures/map.png" alt="由洞壁网格采样的地图"></div><div><img id="hero" alt="当前洞内视点"><div class="controls"><button id="prev">←</button><span id="title"></span><button id="next">→</button></div><p id="pose"></p></div></section>
<div class="thumbs" id="thumbs"></div><details open><summary>场景与图注说明</summary><p>复用 hard_005 的完整洞壁，双回环、两条死路，构建路线总长 __LENGTH__ m。新增 __ROCKS__ 块落石、3 块棋盘板道具。黄色线是构建通道中心线，灰色点来自已知模型表面，红点是相机位置；不代表实测点云或机器人执行轨迹。</p><p>资产加入后，原有贯穿路径在 visual / collision 两套网格上的最小连续净空下界为 __CLEARANCE__ m，要求半径加余量 0.55 m。图像使用程序化岩石材质和检查灯光，未模拟水体；棋盘板不代表已完成标定实验。</p><p><a href="validation.json">路径检查</a> · <a href="views/registered_views.json">相机与地图对应</a> · <a href="assets/manifest.json">道具记录</a> · <a href="verification.json">交付检查</a></p></details>
<dialog id="viewer"><button id="close">关闭</button><img id="full" alt="全尺寸渲染"></dialog></main><script>
const views=__VIEWS__;let current=0;const $=s=>document.querySelector(s);
views.forEach((v,i)=>{let p=document.createElement('button');p.className='pin';p.textContent=v.id;p.title=v.title;p.style.left=v.map_percent[0]+'%';p.style.top=v.map_percent[1]+'%';p.onclick=()=>select(i);$('#map').append(p);let t=document.createElement('button');t.className='thumb';let im=document.createElement('img');im.src=v.image;im.alt=v.title;let s=document.createElement('span');s.textContent=v.id+' · '+v.title;t.append(im,s);t.onclick=()=>select(i);$('#thumbs').append(t)});
function select(i){current=(i+views.length)%views.length;let v=views[current];$('#hero').src=v.image;$('#title').textContent=v.id+' / '+views.length+' · '+v.title;$('#pose').textContent='XYZ '+v.position.map(x=>x.toFixed(2)).join(', ')+' m';document.querySelectorAll('.pin,.thumb').forEach((e,k)=>e.classList.toggle('active',k%views.length===current))}
$('#prev').onclick=()=>select(current-1);$('#next').onclick=()=>select(current+1);$('#hero').onclick=()=>{$('#full').src=views[current].image;$('#viewer').showModal()};$('#close').onclick=()=>$('#viewer').close();document.addEventListener('keydown',e=>{if(e.key==='ArrowLeft')select(current-1);if(e.key==='ArrowRight')select(current+1)});select(0);
</script></html>'''
    html=html.replace('__VIEWS__',payload).replace('__LENGTH__',f"{source['total_route_length_m']:.1f}")
    html=html.replace('__ROCKS__',str(report['rock_count'])).replace('__CLEARANCE__',f"{min(c['continuous_clearance_lower_bound'] for c in report['combined_mesh_path'].values()):.3f}")
    (folder/'index.html').write_text(html,encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder',default='outputs/cave_showcase_hard_v02')
    compose(parser.parse_args().folder)
