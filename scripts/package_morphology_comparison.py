"""Publish the paired geometry inspection and its measured evidence locally."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.verify_textured_exports import verify
from scripts.render_asset_overviews import render


def main(root='exports/morphology_v01',source='outputs/morphology_v01'):
    root=Path(root);source=Path(source)
    entries=[{'difficulty':'controlled_comparison','folder':n,'name':n} for n in ['before','after']]
    verify(root,report_path=root/'verification.json',entries=entries)
    for name in ['before','after']:
        render(root/name)
        for record in ['metrics','validation','provenance','morphology']:
            path=source/name/'metadata'/(record+'.json')
            if path.exists():shutil.copy2(path,root/name/('source_'+record+'.json'))
        with zipfile.ZipFile(root/(name+'_obj.zip'),'w',zipfile.ZIP_DEFLATED) as z:
            for f in [name+'.obj',name+'.mtl','textures/basecolor.png','textures/normal.png','ATTRIBUTION.txt','material_provenance.json']:
                z.write(root/name/f,f)
    for f in ['section_comparison.png','section_comparison.svg','morphology_measurements.json']:
        shutil.copy2(source/f,root/f)
    data=json.loads((root/'morphology_measurements.json').read_text())
    keys=[('area_cv','截面面积变异系数'),('mean_nonconvexity','截面平均非凸度'),
          ('mean_normalized_eccentricity','归一化偏心度'),('max_section_area_gradient_m2_per_m','最大截面面积变化率 / m²·m⁻¹'),
          ('mean_visible_route_lookahead','平均连续可见路线 / m'),('planned_path_clearance','独立路径碰撞网格净空下界 / m')]
    rows=''.join(f'<tr><td>{label}</td><td>{data["cases"]["before"]["summary"][k]:.3f}</td>'
                 f'<td>{data["cases"]["after"]["summary"][k]:.3f}</td></tr>' for k,label in keys)
    views=''
    for i,title in enumerate(['侧洞与悬挑区域','局部顶板下降','成簇落石区域'],1):
        views+=f'<h2>0{i} / {title}</h2><div class="pair">'
        for name,label in [('before','优化前'),('after','优化后')]:
            path=f'{name}/textured_{i:02d}.png'
            views+=f'<figure><a data-view="{name}/{i:02d}" href="{path}"><img src="{path}" alt="{label} · {title}"></a><figcaption>{label} · 相同相机、灯光与材质，点击查看原图</figcaption></figure>'
        views+='</div>'
    ablations=''
    for name,label in [('section_only','仅截面变化'),('roughness_only','仅分区粗糙度'),('features_only','仅局部结构'),('rockfall_only','仅落石簇')]:
        s=data['cases'][name]['summary']
        ablations+=f'<tr><td>{label}</td><td>{s["area_cv"]:.3f}</td><td>{s["mean_nonconvexity"]:.3f}</td><td>{s["planned_path_clearance"]:.3f}</td></tr>'
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cave Composer · 结构不规则性前后对照</title>
<style>*{box-sizing:border-box}body{margin:0;background:#101719;color:#e6eef0;font:16px/1.7 system-ui,sans-serif}
main{max-width:1500px;margin:auto;padding:36px 24px}h1{font-size:32px}h2{font-size:22px;margin-top:34px}p,figcaption{color:#b1c2c8}
a{color:#93d4d5}img{width:100%;display:block;border-radius:5px}figure{margin:0}figcaption{font-size:13px;padding:8px 0}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:18px}.toolbar{position:sticky;top:0;background:#101719ed;padding:12px 0;z-index:2;display:flex;gap:12px;align-items:center}
button{font:inherit;background:transparent;color:#b1c2c8;border:1px solid #50636a;border-radius:5px;padding:6px 15px;cursor:pointer}button[aria-pressed=true]{background:#235760;color:white}
table{border-collapse:collapse;width:100%;margin:18px 0}th,td{text-align:left;border-bottom:1px solid #35474e;padding:10px}th{color:#99cfcf}
.scroll{overflow:auto}.tag{color:#87c8ae;font-size:13px;letter-spacing:2px}.downloads{display:flex;flex-wrap:wrap;gap:16px}.map{max-width:900px;background:white}
footer{border-top:1px solid #35474e;margin-top:32px;padding-top:18px;font-size:13px;color:#a6b9c0}
@media(max-width:700px){.pair{grid-template-columns:1fr}h1{font-size:26px}main{padding:20px 14px}.toolbar{font-size:14px}}
</style><main><div class="tag">CAVE COMPOSER / STRUCTURAL MORPHOLOGY V01</div>
<h1>从规则通道，到可通行的不规则空间</h1>
<p>同一条 50.4 米路线、同一个几何种子与岩壁纹理。优化后加入沿程偏心非凸截面、局部顶板/地板/侧壁变化、侧洞、悬挑、落石簇和分区粗糙度。
全部图像来自实际导出的 GLB。可以切换纯几何模式，排除颜色与法线贴图的影响。</p>
<div class="toolbar"><span>查看模式</span><button data-mode="textured" aria-pressed="true">相同纹理</button><button data-mode="clay" aria-pressed="false">纯几何</button></div>
VIEWS
<h2>实际网格截面与沿程变化</h2><a href="section_comparison.svg"><img src="section_comparison.png" alt="相同位置的前后截面及截面积曲线"></a>
<p>灰色为优化前，青色为优化后；紫色虚线圆是 0.55 米的机器人加余量。来自最终视觉网格的 41 个匹配截面，不是概念示意图。</p>
<div class="scroll"><table><thead><tr><th>诊断量</th><th>优化前</th><th>优化后</th></tr></thead><tbody>ROWS</tbody></table></div>
<p>这些诊断反映结构变化，不代表越大就越真实，也不是训练成功率。前后案例均通过独立 A*、两套最终网格净空与内部检查。
额外导出步骤的两个实际开口和贯穿路径也已验证。</p>
<h2>四个单因素检查</h2><div class="scroll"><table><thead><tr><th>仅启用模块</th><th>面积变异系数</th><th>非凸度</th><th>路径净空下界 / m</th></tr></thead><tbody>ABLATIONS</tbody></table></div>
<p>四个单因素案例与完整前后对照共六个场景，使用同一种子和路线，均通过生成验证。落石簇在本例中对整体面积统计影响较小；局部效果需要结合内部视图检查。</p>
<h2>保持一致的整体路线</h2><img class="map" src="after/overview_route.png" alt="优化后的洞穴及相同构建路线">
<p>新局部侧洞未加入语义导航图；它们可能增加遮挡与自由空间支路，但不承诺每一个侧洞都适合机器人进入。</p>
<h2>模型与验证记录</h2><div class="downloads">
<a href="before/before.glb">优化前 GLB</a><a href="after/after.glb">优化后 GLB</a>
<a href="before_obj.zip">优化前 OBJ 完整包</a><a href="after_obj.zip">优化后 OBJ 完整包</a>
<a href="after/inspection.blend">优化后 Blender</a><a href="verification.json">导出验证</a>
<a href="morphology_measurements.json">原始诊断数据</a><a href="after/source_morphology.json">新增参数与实例位置</a></div>
<footer>本轮实现的是可控结构变化，尚未对真实洞穴进行尺度一致的几何分布拟合或距离测量。
通行性证据限于已检查路径及球形机器人包络；未验证动力学、感知控制误差或策略泛化。
纹理来源：cave-dive-make / Porth Yr Ogof Sump 9，CC BY 4.0。
<a href="after/ATTRIBUTION.txt">署名与修改说明</a> · <a href="render_views.json">相机和灯光记录</a> ·
<a href="deliverable_checksums.json">文件校验</a></footer></main>
<script>document.querySelectorAll('button[data-mode]').forEach(b=>b.onclick=()=>{
document.querySelectorAll('button[data-mode]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));
document.querySelectorAll('a[data-view]').forEach(a=>{const [name,i]=a.dataset.view.split('/');const url=name+'/'+b.dataset.mode+'_'+i+'.png';a.href=url;a.querySelector('img').src=url;});});</script></html>'''
    page=page.replace('VIEWS',views).replace('ROWS',rows).replace('ABLATIONS',ablations)
    config=json.loads((root/'after/config.json').read_text())
    page=page.replace('同一条 50.4 米路线、',f"名义宽 {config['corridor']['width']:.1f} 米、高 {config['corridor']['height']:.1f} 米。同一条 50.4 米路线、")
    page=page.replace('STRUCTURAL MORPHOLOGY V01',root.name.upper().replace('_',' '))
    (root/'index.html').write_text(page,encoding='utf-8')
    hashes={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*'))
            if p.is_file() and p.name!='deliverable_checksums.json' and p.suffix!='.blend1'}
    (root/'deliverable_checksums.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
    print(root/'index.html',len(hashes),'files')


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--root',default='exports/morphology_v01');p.add_argument('--source',default='outputs/morphology_v01')
    args=p.parse_args();main(args.root,args.source)
