"""Package the rendered easy reference-material example as an offline gallery."""
import hashlib
import html
import json
from pathlib import Path
import shutil
import zipfile


def package():
    root = Path('exports/easy_reference_texture_v01')
    folder = root / 'scene_001'
    source = Path('outputs/easy_reference_texture_v01/reference')
    material = json.loads((folder/'material_provenance.json').read_text(encoding='utf-8'))
    metrics = json.loads((source/'metadata/metrics.json').read_text(encoding='utf-8'))
    checks = json.loads((root/'verification.json').read_text(encoding='utf-8'))
    library = json.loads(Path(material['texture_library']).read_text(encoding='utf-8'))
    swatches = root/'swatches'
    swatches.mkdir(exist_ok=True)
    cards = []
    for entry in library['entries']:
        shutil.copy2(Path(material['texture_library']).parent/entry['tile'], swatches/entry['tile'])
        selected = entry['id'] == material['selected_texture_id']
        title = entry['attribution']['title']
        cards.append(f'<figure><img src="swatches/{html.escape(entry["tile"])}" alt="{html.escape(title)}">'
                     f'<figcaption>{html.escape(title)}<br>{"本例选用 · " if selected else ""}'
                     f'{entry["dimensions"][0]} × {entry["dimensions"][1]} px</figcaption></figure>')
    shutil.copy2(source/'materials/rock_albedo.png', root/'selected_texture.png')
    shutil.copy2(source/'metadata/metrics.json', folder/'metrics.json')
    shutil.copy2(source/'metadata/provenance.json', folder/'generation_provenance.json')
    shutil.copy2(source/'metadata/validation.json', folder/'closed_reference_validation.json')
    (root/'texture_library_provenance.json').write_text(json.dumps(library,indent=2),encoding='utf-8')
    with zipfile.ZipFile(root/'cave_easy_reference_001_obj.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for name in ['cave_easy_reference_001.obj','cave_easy_reference_001.mtl','textures/basecolor.png',
                     'textures/normal.png','ATTRIBUTION.txt','material_provenance.json','config.json']:
            archive.write(folder/name,name)
    manifest = {'schema_version':1,'assets':[{'difficulty':'easy','name':'cave_easy_reference_001',
        'folder':'scene_001','source':'outputs/easy_reference_texture_v01/reference',
        'appearance':material['selected_texture_id']}], 'geometry_seed':97001,
        'appearance_seed':material['seed'],'source_role':'development_prior'}
    (root/'batch_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    source_title = html.escape(material['reference_texture']['attribution']['title'])
    source_url = html.escape(material['reference_texture']['attribution']['source'],quote=True)
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cave Composer · 真实参考纹理 Easy 示例</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#101719;color:#e5ecee;font:16px/1.7 system-ui,sans-serif}
main{max-width:1400px;margin:auto;padding:42px 28px}h1{font-size:34px;margin:8px 0}h2{font-size:23px;margin:30px 0 12px}
p{color:#b3c2c8;max-width:960px}a{color:#8dd6d6}nav{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0}
nav a{border:1px solid #43565d;padding:9px 16px;border-radius:6px;text-decoration:none}
img{display:block;width:100%;height:auto;border-radius:7px}figure{margin:0}figcaption{font-size:14px;color:#b3c2c8;padding:9px 0 18px}
.views,.details{display:grid;grid-template-columns:1fr 1fr;gap:20px}.swatches{display:grid;grid-template-columns:repeat(4,1fr);gap:20px}
.swatches img{aspect-ratio:1;object-fit:cover}.tag{color:#89ccae;font-size:13px;letter-spacing:2px}.map{background:white}
.facts{display:flex;gap:28px;flex-wrap:wrap;border-block:1px solid #30434a;padding:18px 0;margin:22px 0;color:#b3c2c8}
.facts strong{font-size:24px;color:#e5ecee}footer{border-top:1px solid #30434a;margin-top:32px;padding-top:20px;font-size:13px;color:#9bafb7}
@media(max-width:700px){main{padding:24px 16px}h1{font-size:27px}.views,.details{grid-template-columns:1fr}.swatches{grid-template-columns:1fr 1fr}}
</style><main>
<span class="tag">CAVE COMPOSER / EASY / REFERENCE APPEARANCE</span>
<h1>真实岩壁纹理，应用到自动生成洞穴</h1>
<p>本例从 SOURCE_TITLE 的扫描纹理中选取岩壁局部，处理平铺边缘后应用到程序生成的洞穴。
下方视图直接渲染自导出的 GLB；使用中性检查灯光，没有烘焙水体效果。</p>
<nav><a href="scene_001/cave_easy_reference_001.glb" download>下载 GLB · 内嵌贴图</a>
<a href="cave_easy_reference_001_obj.zip" download>下载 OBJ 完整包</a>
<a href="scene_001/cave_easy_reference.blend">Blender 检查场景</a><a href="verification.json">导出验证记录</a></nav>
<div class="facts"><span><strong>LENGTH m</strong> 主通道</span><span><strong>2</strong> 缓弯</span>
<span><strong>2</strong> 实际开口</span><span><strong>4K</strong> 导出 UV 贴图</span></div>
<figure><a href="scene_001/inside_01.png"><img src="scene_001/inside_01.png" alt="洞穴内部第一视角：灰蓝色岩壁和宽阔通道"></a>
<figcaption>01 / 入口后方 · 原始渲染 1800 × 1125，点击查看大图。</figcaption></figure>
<div class="views"><figure><a href="scene_001/inside_02.png"><img src="scene_001/inside_02.png" alt="洞穴中段岩壁"></a><figcaption>02 / 洞穴中段</figcaption></figure>
<figure><a href="scene_001/inside_03.png"><img src="scene_001/inside_03.png" alt="洞穴后段内部"></a><figcaption>03 / 洞穴后段</figcaption></figure></div>
<h2>整体洞穴与贯穿路径</h2><div class="details">
<figure><img class="map" src="scene_001/overview_route.png" alt="整体轨迹俯视图"><figcaption>青色：构建路线；紫色虚线：检查过的贯穿路径。入口与出口均为实际开口。</figcaption></figure>
<figure><img class="map" src="scene_001/overview_profile.png" alt="洞穴高度剖面"><figcaption>全长高度剖面。GLB 与 OBJ 的开口、几何和贯穿路径检查均通过。</figcaption></figure></div>
<h2>首批可抽样纹理</h2><p>4 块已筛选的岩壁纹理，来自 3 个扫描资产、2 组洞穴来源。
批量生成时按外观种子选择纹理；本例固定使用 Sump 9 的灰蓝色岩壁局部。</p>
<div class="swatches">SWATCHES</div>
<p>这些是原扫描图集中的 132–224 像素局部，保留了一些采集光照；4K 指导出贴图的分辨率。
法线细节来自程序材质，粗糙度为配置值。新纹理已接入生成与导出流程，泛化收益仍需训练实验验证。</p>
<footer>参考资产：<a href="SOURCE_URL">SOURCE_TITLE</a> · cave-dive-make · CC BY 4.0。
处理记录：岩壁裁剪、周期边缘处理、种子旋转、投影与 UV 烘焙。
<a href="scene_001/ATTRIBUTION.txt">本例署名</a> · <a href="texture_library_provenance.json">全部纹理来源</a> ·
<a href="scene_001/render_views.json">渲染视角</a> · <a href="deliverable_checksums.json">文件校验</a>
<p>Geometry seed 97001 / Appearance seed 97011 · 来源归入开发先验。</p></footer></main></html>'''
    page = page.replace('SOURCE_TITLE',source_title).replace('SOURCE_URL',source_url)
    page = page.replace('LENGTH',f'{metrics["main_route_length"]:.1f}').replace('SWATCHES',''.join(cards))
    (root/'index.html').write_text(page,encoding='utf-8')
    hashes = {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(root.rglob('*')) if p.is_file() and p.name!='deliverable_checksums.json'
              and p.suffix!='.blend1'}
    (root/'deliverable_checksums.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
    print(root/'index.html',len(hashes),'files packaged')


if __name__=='__main__':
    package()
