"""Build a portable local gallery from measured scene bundles; no web service needed."""
import argparse
import html
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps


LABELS = {
    'cave_a_simple': ('A / Mostly straight', '长而宽的主通道'),
    'cave_b_sharp_turns': ('B / Sharp turns', '60°、90°、120° 弯道'),
    'cave_c_s_turn': ('C / S-turn', '左转、右转、再急左转'),
    'cave_d_branching': ('D / Branching', '分叉与两个死路'),
    'cave_e_chamber': ('E / Chamber', '窄入口、多瓣大厅、窄出口'),
    'cave_f_vertical': ('F / Vertical', '上坡、下坡与垂向变化'),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='outputs/final')
    args = parser.parse_args()
    root = Path(args.root)
    cards = []
    for name, (label, description) in LABELS.items():
        folder = root / name
        metrics = json.loads((folder / 'metadata/metrics.json').read_text())
        validation = json.loads((folder / 'metadata/validation.json').read_text())
        clearance = validation['mesh']['collision']['continuous_polyline_clearance_lower_bound']
        cards.append(f'''<article>
          <div class="heading"><h2>{html.escape(label)}</h2><span class="badge">{validation['status']}</span></div>
          <p>{description}</p>
          <a class="preview-link" href="{name}/previews/overview.png"><img data-scene="{name}" src="{name}/previews/overview.png" alt="{label} 总览"></a>
          <dl><div><dt>全路线长度</dt><dd>{metrics['total_length']:.1f} m</dd></div>
          <div><dt>测量最窄宽度</dt><dd>{metrics['minimum_width']:.2f} m</dd></div>
          <div><dt>高程范围</dt><dd>{metrics['vertical_range']:.2f} m</dd></div>
          <div><dt>碰撞净空下界</dt><dd>{clearance:.2f} m</dd></div></dl>
          <nav aria-label="{label} 文件"><a href="{name}/cave.blend">Blender 场景</a><a href="{name}/metadata/metrics.json">指标</a><a href="{name}/metadata/validation.json">验证</a><a href="{name}/metadata/config.yaml">配置</a><a href="{name}/stonefish/cave.scn">Stonefish XML</a></nav>
        </article>''')
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cave Composer · V0 gallery</title><style>
:root{color-scheme:dark;font-family:system-ui,"Microsoft YaHei",sans-serif;background:#10191e;color:#e5edf1}
*{box-sizing:border-box}body{max-width:1500px;margin:auto;padding:36px 24px 70px}h1{font-size:clamp(28px,4vw,48px);margin:10px 0}h2{font-size:20px;margin:0}
p{color:#b7c8d0;line-height:1.75}a{color:#83d8ca;text-underline-offset:4px}.eyebrow{letter-spacing:.18em;color:#83d8ca;font-size:12px}.intro{max-width:900px}
.toolbar{display:flex;flex-wrap:wrap;gap:9px;margin:26px 0;position:sticky;top:0;background:#10191ef0;padding:14px 0;z-index:1}
button{font:inherit;background:#22333d;border:1px solid #4b6572;border-radius:7px;padding:9px 20px;color:inherit;cursor:pointer}button[aria-pressed=true]{background:#83d8ca;color:#10252a;border-color:#83d8ca}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}article{background:#18262e;border:1px solid #304650;border-radius:12px;overflow:hidden;padding:20px}.heading{display:flex;justify-content:space-between;align-items:center;gap:12px}.badge{font-size:12px;color:#9aead1;border:1px solid #427966;border-radius:20px;padding:4px 9px}
article p{margin:8px 0 16px}article img{display:block;width:100%;aspect-ratio:1.6;object-fit:contain;background:#10191e;border-radius:6px}dl{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:18px 0}dt{font-size:12px;color:#a9bbc5}dd{margin:4px 0 0;font-size:20px}nav{display:flex;flex-wrap:wrap;gap:14px;font-size:13px}.material{margin-top:36px;padding:26px;border:1px solid #304650;border-radius:12px}.material img{width:100%;max-width:1100px;display:block;margin-top:18px}.footnote{font-size:13px}
@media(max-width:850px){.grid{grid-template-columns:1fr}body{padding:22px 14px}dl{grid-template-columns:repeat(2,1fr)}}
</style><body><header><div class="eyebrow">AUTOMATED CAVE COMPOSER / V0</div><h1>六种洞穴，同一套可验证生成契约</h1>
<p class="intro">显式弯道、分支、大厅和坡度 → 独立视觉与碰撞网格 → 导航真值与净空验证。以下为实际生成的 Blender 渲染。总览剖去顶部便于观察，导出的完整网格保持封闭；内部视角没有加入水体效果。</p>
<nav><a href="../../CAVE_COMPOSER_V0_REPORT.md">完整报告</a><a href="contact_sheet.jpg">六场景总览图</a><a href="inside_contact_sheet.jpg">内部视角拼图</a><a href="../../docs/cavers_material_experiment.md">CAVERS 实验记录</a></nav></header>
<div class="toolbar" role="group" aria-label="切换全部场景的视角"><button data-view="overview" aria-pressed="true">总览</button><button data-view="inside_01" aria-pressed="false">内部视角 1</button><button data-view="inside_02" aria-pressed="false">内部视角 2</button><button data-view="topology" aria-pressed="false">拓扑 / 视距</button></div>
<main class="grid">''' + '\n'.join(cards) + '''</main>
<section class="material"><h2>CAVERS 真实洞壁 → 新材质</h2><p>从本机两帧岩壁 ROI 提取灰褐调色板，并用视觉判断设置轻微方向性。左侧为默认材质，右侧为 CAVERS 参考材质；相机与照明一致，两个 OBJ 和两个网格数组文件均保持字节相同。颜色仍包含采集照明影响，roughness 为默认值。</p>
<a href="../material_experiment/cavers_transfer/appearance_comparison.jpg"><img src="../material_experiment/cavers_transfer/appearance_comparison.jpg" alt="相同洞穴几何的默认与 CAVERS 参考材质对照"></a>
<p><a href="../material_experiment/cavers/cavers_contact.jpg">真实候选帧</a> · <a href="../material_experiment/cavers_transfer/experiment.json">外观来源与原始文件校验</a></p></section>
<p class="footnote">VALID 的范围是离线网格与球形机器人路线验证。自相交使用浮点 BVH 检查；不构成精确几何证明。Stonefish 接口为 PARTIAL，尚未在模拟器中运行。可点击预览打开原图。</p>
<script>
document.querySelectorAll('button[data-view]').forEach(button=>button.addEventListener('click',()=>{
  document.querySelectorAll('button[data-view]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
  document.querySelectorAll('img[data-scene]').forEach(img=>{const path=`${img.dataset.scene}/previews/${button.dataset.view}.png`;img.src=path;img.parentElement.href=path;img.alt=img.dataset.scene+' '+button.textContent;});
}));
</script></body></html>'''
    (root / 'gallery.html').write_text(page, encoding='utf-8')
    try:
        font = ImageFont.truetype('DejaVuSans.ttf', 22)
    except OSError:
        font = ImageFont.load_default(size=22)
    for view, filename in [('overview', 'contact_sheet.jpg'), ('inside_01', 'inside_contact_sheet.jpg')]:
        sheet = Image.new('RGB', (1600, 1668), '#10191e')
        draw = ImageDraw.Draw(sheet)
        for index, (name, (label, _)) in enumerate(LABELS.items()):
            x, y = (index % 2) * 800, (index // 2) * 556
            with Image.open(root / name / 'previews' / f'{view}.png') as source:
                tile = ImageOps.contain(source.convert('RGB'), (780, 488))
                sheet.paste(tile, (x + (800-tile.width)//2, y+52))
            draw.text((x+18,y+14), label, font=font, fill='#e5edf1')
        sheet.save(root / filename, quality=93)
    print(root / 'gallery.html')


if __name__ == '__main__':
    main()
