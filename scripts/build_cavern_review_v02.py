"""Build a local review gallery from actual v02 evidence and frozen asset links."""
from pathlib import Path
import html
import json
import os

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/cavern_round_v02'
FIG=ROOT/'overleaf/figures/generated/c1_v02'

def relative(path):
    return Path(os.path.relpath(path,OUT)).as_posix()

def link(path,label):
    return f'<a href="{html.escape(relative(path))}">{html.escape(label)}</a>'

def main():
    data=json.loads((ROOT/'outputs/c1_pilot_v02/summary.json').read_text())
    release=ROOT/'exports/cavern_pretraining_v02'
    manifest=json.loads((release/'manifest.json').read_text())
    head='''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CAVERN v02 · 实验与资产验收</title>
<style>body{font:16px/1.65 system-ui,"Microsoft YaHei",sans-serif;color:#273444;background:#f5f7f9;margin:0}main{max-width:1120px;margin:30px auto;padding:0 24px}h1{font-size:30px}h2{font-size:23px;margin-top:40px}a{color:#087a90}nav{display:flex;gap:22px;flex-wrap:wrap}figure{margin:24px 0;padding:20px;background:white;border:1px solid #dce2e7}img{display:block;width:100%;height:auto}figcaption{font-size:14px;margin-top:15px}table{border-collapse:collapse;width:100%;background:white}td,th{padding:10px;border-bottom:1px solid #dce2e7;text-align:left}small{color:#63717d}.note{border-left:3px solid #b64282;padding:8px 18px;background:white}code{overflow-wrap:anywhere}details{margin-top:20px}</style><main>
<h1>CAVERN v02 · 实验与资产验收</h1>
<p>本页来自实际生成网格、几何检查记录和 Isaac Sim 运行。没有策略轨迹或生成式实验图像。</p><nav>'''
    parts=[head,link(ROOT/'overleaf/build/main.pdf','论文 PDF'),
        link(ROOT/'outputs/cavern_paper_v02/overleaf_draft.zip','Overleaf 源码 ZIP'),
        link(ROOT/'research_workspace/ROUND_V02_REPORT.md','完整执行报告'),
        link(ROOT/'research_workspace/COLLABORATOR_HANDOFF_v02.md','同学接手说明'),
        '</nav><h2>C1 · 六个固定请求，三个生成条件</h2>',
        '<p>4 个正常请求 + 2 个压力请求，每个条件只生成一次。下表使用已声明的 OBJ 接缝重检结果；原始导入拒绝保留。各条件共享 base request，不是 18 个独立洞穴。</p>',
        '<table><tr><th>条件</th><th>正常通过</th><th>压力通过</th><th>全部生成尝试</th></tr>']
    for arm,label in [('full','完整 Composer'),('no_protection','关闭通行保护'),('restricted','受限生成')]:
        groups=[g for g in data['groups'] if g['arm']==arm]
        normal=next(g for g in groups if g['stratum']=='normal');stress=next(g for g in groups if g['stratum']=='stress')
        parts.append(f"<tr><td>{label}</td><td>{normal['final_passes']}/{normal['requested']}</td><td>{stress['final_passes']}/{stress['requested']}</td><td>{sum(g['attempts'] for g in groups)}</td></tr>")
    parts.extend(['</table><p class="note">这是描述性 pilot。完整方法在一个压力请求中优于关闭保护，但受限几何的整体产出更高；不能据此声称统计优势。PLUME 的真实运行被依赖与 Blender API 问题阻塞，没有数值对照。</p>',
        link(ROOT/'outputs/c1_pilot_v02/results.csv','逐请求指标 CSV')+' · '+link(ROOT/'outputs/c1_pilot_v02/delivery_recheck.json','最终导入重检')])
    figures=[
        ('fixed_cave_cases','固定样本：同一相机、尺度和真实网格，上排 clay，下排 textured。切顶仅用于检查；标注为实际截面跨度均值，包含分岔/腔室。'),
        ('protection_actual_geometry','同请求、同 seed 的保护消融。灰点为网格三角面中心投影；青色为构造路线，洋红虚线为搜索路径。关闭保护一侧是保留的失败诊断：红色 S/G 不满足保守栅格端点条件；55% 处剖面不等同于端点失败位置。'),
        ('pilot_quantitative','正常与压力分开统计；耗时包含失败及两轮交付检查。没有通过时，单位有效洞穴成本为 n/a。'),
        ('fixed_cave_interiors','匹配的真实 Blender 内部视角。用于检查几何与纹理，不是运行策略的观测轨迹。'),
        ('isaac_stereo_actual','实际 Isaac Sim 5.0.0.0 输出：两个不同洞穴的左右 RGB，1280×720、12 cm 基线。只证明记录中的静态网格、reset 位置、碰撞探针与相机流程；诊断照明未经水下校准。')]
    for name,caption in figures:
        parts.append(f'<figure><img loading="lazy" src="{relative(FIG/(name+".png"))}" alt="{html.escape(name)}"><figcaption>{html.escape(caption)}<br>'+link(FIG/(name+'.pdf'),'PDF')+' · '+link(FIG/(name+'.svg'),'可编辑 SVG')+'</figcaption></figure>')
    parts.append('<h2>C2 · 冻结的训练前接口包</h2><p>8 个场景，24 个固定任务，其中主配对任务 16 个、辅助任务 8 个。各条件为 train 2 / development 1 / generated ID test 1；新 seed 不自动称为 OOD。实际净空仍不完全匹配，实际训练接口仍为 UNCONFIRMED。</p><table><tr><th>场景</th><th>Split</th><th>纹理资产</th><th>碰撞</th></tr>')
    for s in manifest['scenes']:
        parts.append(f'<tr><td>{s["scene_id"]}</td><td>{s["split"]}</td><td>'+link(release/s['visual_glb'],'GLB')+' · '+link(release/s['visual_obj'],'OBJ + 同目录 MTL/PNG')+'</td><td>'+link(release/s['collision_obj'],'静态三角面 OBJ')+'</td></tr>')
    parts.append('</table><p>'+link(release/'manifest.json','冻结 manifest')+' · '+link(release/'verification.json','最终几何检查')+' · '+link(release/'episodes.json','固定 episode 清单')+'</p>')
    parts.append('<h2>C3 · 来源与任务资格</h2><p>真实来源的尺度、部分来源身份和未接触资格尚待确认。本轮固定了资格与短片段任务规则，没有使用最终资产调生成器，也没有真实迁移成绩。</p><details><summary>查看已有裁剪准备图（本地工作材料）</summary><figure><img loading="lazy" src="'+relative(FIG/'real_source_preparation.png')+'" alt="既有 Metashape 裁剪准备图"><figcaption>复用旧裁剪图；未定标、未批准为 untouched test，不是本轮新选定的正式测试区域。</figcaption></figure></details>')
    parts.append('<p><small>旧难度图鉴继续保留：'+link(ROOT/'exports/caves_difficulty_v01/index.html','30 个历史场景')+'。当前包是独立版本；请只使用提供的源码 ZIP 导入 Overleaf，原始扫描和私有来源图不在该 ZIP 内。</small></p></main></html>')
    (OUT/'index.html').write_text('\n'.join(parts),encoding='utf-8')
    print(OUT/'index.html')

if __name__=='__main__':main()
