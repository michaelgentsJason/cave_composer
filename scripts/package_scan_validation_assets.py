"""Package the two reviewed real-scan validation crops with opening checks."""
import hashlib,json,zipfile
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path('exports/metashape_crops_v01')
NAMES=['zhaoqing_validation_short','catacombs_validation_short']
FILES=['cave.glb','cave.obj','cave.mtl','appearance.png','inspection.blend',
       'route.json','crossing_candidate_route.json','opening_check.json','route_check.json',
       'metadata.json','export_report.json','inside_01.png','inside_02.png','render_views.json',
       'ASSET_README.md','openings_and_path.png']


def sha(path):
    value=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):value.update(block)
    return value.hexdigest()


def main():
    manifest={'scale_status':'unverified_model_units','physical_navigation_certified':False,'assets':[]}
    for name in NAMES:
        folder=ROOT/name;check=json.loads((folder/'opening_check.json').read_text())
        assert check['both_endpoints_connected_to_crop_exterior_without_observed_triangle_contact']
        crossing=json.loads((folder/'crossing_candidate_route.json').read_text());route=np.array(crossing['points'])
        d=np.load(folder/'source_crop.npz');v=d['vertices'];rgb=d['colors'];rng=np.random.default_rng(54)
        idx=rng.choice(len(v),min(100000,len(v)),replace=False)
        fig,ax=plt.subplots(figsize=(10,6),layout='constrained')
        ax.scatter(v[idx,0],v[idx,1],c=rgb[idx],s=.25,alpha=.6,rasterized=True)
        original=np.array(json.loads((folder/'route.json').read_text())['points'])
        ax.plot(original[:,0],original[:,1],color='#168c9e',lw=2,label='Recorded-route candidate')
        for i,key in enumerate(['start_extension','goal_extension']):
            points=np.array(check[key]['points']);ax.plot(points[:,0],points[:,1],color='#bc7922',lw=2,ls='--',label='Checked extension to crop exterior' if i==0 else None)
        for label,point in [('A',route[0]),('B',route[-1])]:
            ax.scatter(*point[:2],color='#b64282',s=40,zorder=6);ax.annotate(label,point[:2],xytext=(6,6),textcoords='offset points',color='#b64282',fontsize=13)
        ax.set_aspect('equal');ax.set_xlabel('X / uncalibrated model units');ax.set_ylabel('Y / model units')
        ax.set_title(name+'\nObserved-triangle clearance only; scan completeness unverified');ax.legend(loc='best',fontsize=9)
        fig.savefig(folder/'openings_and_path.png',dpi=180);plt.close(fig)
        readme=f'''# {name}

这是从真实 Metashape 重建中裁剪的短验证段。原始采集外观保留，未增加封口面。

## 文件使用

- `cave.glb`：纹理内嵌，可单文件导入。
- `cave.obj`、`cave.mtl`、`appearance.png`：三者须放在同一目录。
- `inspection.blend`：Blender 检查文件，保留原始顶点颜色和内部相机。
- `route.json`：筛选后的内部候选路线。
- `crossing_candidate_route.json`：增加两端延伸后的候选路线，从裁剪范围外的 A 点到范围外的 B 点。
- `openings_and_path.png`：开口附近与路线的俯视示意；`opening_check.json` 记录检查详情。

OBJ、路线 JSON 均使用 Z-up 的归一化源坐标。GLB 使用 Y-up，换算 `(x,y,z) -> (x,z,-y)`；没有改变比例。

## 实际确认的范围

- 焊接裁剪接缝后有 {check['boundary_edges_after_welding']} 条边界边，模型为开口表面。
- A 端延伸穿过 `{check['start_extension']['crossed_plane']}`，B 端穿过 `{check['goal_extension']['crossed_plane']}`。
- 连续候选路线及两端延伸对已重建三角面的距离下界为 {crossing['surface_distance_lower_bound']:.6f} **模型单位**。
- Catacombs 的两端均穿过 X_min 裁剪面，但位置不同；这不是声称两个原生洞口已被重建或识别。

尺度尚未定标，所有长度都不是米。开口包括裁剪边界，也包括原扫描缺面；这不是完整墙体/封闭自由空间或真实机器人通行证书。缺面不能当作自由空间。正式导航前需定标、检查缺面，并验证机器人包络及碰撞模型。

本资产是同一来源洞穴中的空间留出验证段，不是独立未见洞穴的 zero-shot 证据。颜色贴图由原始顶点 RGB 烘焙，包含采集时的光照，未恢复物理 PBR。
'''
        (folder/'ASSET_README.md').write_text(readme,encoding='utf-8')
        hashes={file:sha(folder/file) for file in FILES}
        (folder/'asset_checksums.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
        target=ROOT/f'{name}.zip'
        with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as bundle:
            for file in FILES+['asset_checksums.json']:bundle.write(folder/file,arcname=f'{name}/{file}')
        with zipfile.ZipFile(target) as bundle:
            for file,expected in hashes.items():
                digest=hashlib.sha256()
                with bundle.open(f'{name}/{file}') as stream:
                    for block in iter(lambda:stream.read(8*1024*1024),b''):digest.update(block)
                assert digest.hexdigest()==expected,file
        manifest['assets'].append({'name':name,'folder':name,'archive':target.name,'archive_bytes':target.stat().st_size,
            'sha256':sha(target),'both_endpoints_cross_crop_boundary':True,
            'observed_triangle_clearance_lower_bound_model_units':crossing['surface_distance_lower_bound'],
            'archive_contents_hash_verified':True})
        print(name,'PACKAGED_AND_VERIFIED',target.stat().st_size,flush=True)
    (ROOT/'validation_exports.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    page=ROOT/'index.html';html=page.read_text(encoding='utf-8')
    start='<!-- validation asset downloads -->';end='<!-- end validation asset downloads -->'
    if start in html:html=html[:html.index(start)]+html[html.index(end)+len(end):]
    section=start+'<h2>短验证段资产包 · 开口与路线补充检查</h2><p>已检查两端延伸路线穿过裁剪边界，并与已重建表面保持正距离。尺度与缺面仍待确认。</p>'
    for name in NAMES:
        section+=f'<article><h3>{name}</h3><img src="{name}/openings_and_path.png" loading="lazy"><p><a href="{name}.zip">下载完整资产 ZIP（GLB + OBJ/MTL/PNG + Blender + 路线/检查）</a> · <a href="{name}/ASSET_README.md">使用说明</a></p></article>'
    section+=end
    page.write_text(html.replace('</main>',section+'</main>'),encoding='utf-8')


if __name__=='__main__':main()
