"""Portable asset gallery with whole-cave route and interior views."""
import html
from pathlib import Path


def write_gallery(root, assets, targets):
    root = Path(root)
    counts = {tier: sum(a['difficulty'] == tier for a in assets) for tier in targets}
    cards = []
    for a in assets:
        folder, name = a['folder'], html.escape(a['name'], quote=True)
        overview = f'{folder}/overview_route.png'
        if not (root / overview).exists():
            overview = f'{folder}/preview_glb_interior.png'
        interior = f'{folder}/preview_glb_interior.png'
        profile = f'{folder}/overview_profile.png' if (root/folder/'overview_profile.png').exists() else ''
        cards.append(f'''<article data-tier="{a['difficulty']}">
<div class="card-heading"><h2>{name}</h2><span class="badge">{a['difficulty']}</span></div>
<button class="image-button route-preview" data-src="{overview}" data-profile="{profile}" data-name="{name}" onclick="enlarge(this)" aria-label="放大 {name} 整体轨迹"><img loading="lazy" src="{overview}" alt="{name} 整体洞穴轨迹"><span>查看整体轨迹 ↗</span></button>
<button class="image-button interior-preview" data-src="{interior}" data-name="{name}" onclick="enlarge(this)" aria-label="放大 {name} 内部纹理"><img loading="lazy" src="{interior}" alt="{name} 内部纹理"><span>查看内部纹理 ↗</span></button>
<p class="metrics">主路 <b>{a['main_route_length_m']:.1f} m</b> · 含分支 <b>{a['total_route_length_m']:.1f} m</b><br>名义宽度 {a['nominal_width_m']:.2f} m · 死路 {a.get('dead_ends', a['branches'])} · 回环 {a.get('loops', 0)} · 洞厅 {a['chambers']}{('<br>路线高差 ' + format(a['elevation_range_m'], '.1f') + ' m') if 'elevation_range_m' in a else ''}</p>
<div class="downloads"><a href="{folder}/{a['name']}.glb">GLB</a><a href="{folder}/{a['name']}.obj">OBJ</a><a href="{folder}/{a['name']}.mtl">MTL</a><a href="{folder}/textures/basecolor.png">颜色贴图</a><a href="{folder}/textures/normal.png">法线贴图</a><a href="{folder}/navigation_z_up.json">导航路径</a></div></article>''')
    page = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Cave Composer · 整体洞穴轨迹</title>
<style>*{box-sizing:border-box}body{font:15px/1.6 system-ui,sans-serif;background:#f5f3ef;color:#273444;margin:30px auto;max-width:1500px;padding:0 24px}
h1{font-size:30px;margin-bottom:2px}h2{font-size:18px;margin:0}.subtle{color:#64727c}.toolbar{display:flex;gap:20px;flex-wrap:wrap;justify-content:space-between;margin:22px 0 12px}
.group{display:flex;gap:7px;flex-wrap:wrap}button{font:inherit;cursor:pointer;border:1px solid #cad3d6;background:white;color:#273444;border-radius:6px;padding:7px 16px}button[aria-pressed=true]{background:#273444;color:white;border-color:#273444}
.legend{display:flex;gap:20px;flex-wrap:wrap;font-size:13px;margin:12px 0 22px}.key{display:inline-block;width:25px;vertical-align:middle;margin-right:6px;border-top:3px solid}.main-key{color:#168c9e}.branch-key{color:#bb7c26}.loop-key{color:#5274b8}.path-key{color:#b64282;border-top-style:dashed}.rock-key{height:10px;background:#dce5e3;border:0}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,410px),1fr));gap:22px}article{background:white;border-radius:12px;overflow:hidden;padding:18px}article[hidden]{display:none}.card-heading{display:flex;justify-content:space-between;align-items:center;gap:10px}.badge{font-size:12px;color:#64727c}
.image-button{position:relative;width:100%;padding:0;border:0;background:white;margin:12px 0 0}.image-button img{display:block;width:100%;height:auto}.image-button span{position:absolute;right:10px;bottom:8px;font-size:12px;background:#ffffffed;padding:2px 8px;border-radius:4px;color:#47606d}.metrics{font-size:13px;margin:10px 0 14px}.downloads{display:flex;gap:14px;flex-wrap:wrap;font-size:13px}a{color:#168c9e}
body[data-view=route] .interior-preview,body[data-view=interior] .route-preview{display:none}
dialog{width:min(1250px,96vw);max-height:95vh;border:0;border-radius:12px;padding:20px;background:white;color:#273444}dialog::backdrop{background:#17232ed9}dialog img{display:block;width:100%;height:auto}#viewer-profile[hidden]{display:none}dialog .dialog-top{display:flex;justify-content:space-between;gap:16px;align-items:center}.dialog-note{font-size:13px;color:#64727c}
@media(max-width:600px){body{padding:0 12px;margin:18px auto}h1{font-size:24px}article{padding:12px}.legend{gap:10px}.toolbar{gap:12px}dialog{padding:12px}}
</style></head><body data-view="route"><h1>Cave Composer · 整体洞穴轨迹</h1>'''
    page += f'<p class="subtle">Easy {counts["easy"]}/{targets["easy"]} · Medium {counts["medium"]}/{targets["medium"]} · Hard {counts["hard"]}/{targets["hard"]}</p>'
    page += '<p class="subtle">查看完整通道、分支与入口出口。点击图片放大，或切换到内部纹理。</p><div class="toolbar"><div class="group" aria-label="难度筛选">'
    page += ''.join(f'<button data-filter="{t}" aria-pressed="{str(t == "all").lower()}" onclick="filterTier(\'{t}\')">{label}</button>'
                    for t, label in [('all', '全部'), ('easy', 'easy'), ('medium', 'medium'), ('hard', 'hard')])
    page += '''</div><div class="group" aria-label="视图切换"><button data-view="route" aria-pressed="true" onclick="setView('route')">整体轨迹</button><button data-view="interior" aria-pressed="false" onclick="setView('interior')">内部纹理</button></div></div>
<div class="legend"><span><i class="key rock-key"></i>实际网格俯视投影</span><span><i class="key main-key"></i>主通道参考线</span><span><i class="key branch-key"></i>死路支路</span><span><i class="key loop-key"></i>回环支路</span><span><i class="key path-key"></i>已验证贯穿路径</span><span>● 入口　◆ 出口</span></div>
<p class="subtle" style="font-size:12px">俯视图为 XY 投影；每张图等比例显示，实际长度请参考标尺。路径含洞口外的短距离接近段。</p><main>'''
    page += ''.join(cards)
    page += '''</main><dialog id="viewer"><div class="dialog-top"><h2 id="viewer-title"></h2><button onclick="document.getElementById('viewer').close()">关闭 ✕</button></div><img id="viewer-image" alt="放大视图"><img id="viewer-profile" hidden alt="主通道高程剖面"><p class="dialog-note">Entrance / Exit 为实际洞口位置。洋红虚线为已验证路径，金色线为死路支路，蓝色线为回环支路。</p><a id="viewer-original" target="_blank" rel="noopener">打开原图</a></dialog>
<script>function filterTier(t){document.querySelectorAll('article').forEach(e=>e.hidden=t!=='all'&&e.dataset.tier!==t);document.querySelectorAll('[data-filter]').forEach(e=>e.setAttribute('aria-pressed',e.dataset.filter===t))}
function setView(v){document.body.dataset.view=v;document.querySelectorAll('button[data-view]').forEach(e=>e.setAttribute('aria-pressed',e.dataset.view===v))}
function enlarge(button){const d=document.getElementById('viewer');document.getElementById('viewer-title').textContent=button.dataset.name;document.getElementById('viewer-image').src=button.dataset.src;const profile=document.getElementById('viewer-profile');profile.hidden=!button.dataset.profile;if(button.dataset.profile)profile.src=button.dataset.profile;else profile.removeAttribute('src');document.getElementById('viewer-original').href=button.dataset.src;d.showModal()}
document.getElementById('viewer').addEventListener('click',e=>{if(e.target===e.currentTarget){const r=e.currentTarget.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.currentTarget.close()}});
</script></body></html>'''
    (root / 'index.html').write_text(page, encoding='utf-8')
