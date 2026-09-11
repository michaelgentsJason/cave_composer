"""Audit source separation and export bytes, then build a local review gallery."""
import hashlib,json,struct
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT=Path('exports/metashape_crops_v01')
RAW=Path('outputs/metashape_crops_v01')


def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for b in iter(lambda:stream.read(8*1024*1024),b''):digest.update(b)
    return digest.hexdigest()


def verify_glb(folder):
    with (folder/'cave.glb').open('rb') as stream:
        magic,version,length=struct.unpack('<4sII',stream.read(12));assert magic==b'glTF' and version==2
        assert length==(folder/'cave.glb').stat().st_size
        size,kind=struct.unpack('<I4s',stream.read(8));assert kind==b'JSON'
        doc=json.loads(stream.read(size));binary_size,kind=struct.unpack('<I4s',stream.read(8));assert kind==b'BIN\x00'
        base=stream.tell();attrs=doc['meshes'][0]['primitives'][0]['attributes']
        acc=doc['accessors'][attrs['POSITION']];view=doc['bufferViews'][acc['bufferView']]
        d=np.load(folder/'source_crop.npz');v=d['vertices'];faces=d['faces'];assert acc['count']==len(faces)*3
        idx=np.linspace(0,len(faces)*3-1,2000,dtype=int)
        for i in idx:
            stream.seek(base+view['byteOffset']+int(i)*12)
            xyz=np.frombuffer(stream.read(12),dtype='<f4');expected=v[faces.reshape(-1)[i]][[0,2,1]].copy();expected[2]*=-1
            assert np.array_equal(xyz,expected)
        iv=doc['bufferViews'][doc['images'][0]['bufferView']];stream.seek(base+iv['byteOffset'])
        assert stream.read(iv['byteLength'])==(folder/'appearance.png').read_bytes()
        assert doc['materials'][0]['doubleSided'] and 'KHR_materials_unlit' in doc['extensionsUsed']
    objcounts={'v':0,'vt':0,'vn':0,'f':0}
    with (folder/'cave.obj').open() as stream:
        for line in stream:
            tag=line.split(' ',1)[0]
            if tag in objcounts:objcounts[tag]+=1
    assert objcounts=={'v':len(v),'vt':len(faces)*3,'vn':len(v),'f':len(faces)},objcounts
    return {'glb_sampled_positions_exact':True,'embedded_texture_exact':True,'obj_counts':objcounts}


def main():
    manifest=json.loads((ROOT/'manifest.json').read_text());checks={'sources':{},'assets':{}}
    for source in ['zhaoqing','catacombs']:
        inv=json.loads((RAW/source/'inventory.json').read_text())
        hashes={p:sha(Path(inv['source'])/p)==h for p,h in inv['source_hashes'].items()}
        assert all(hashes.values()),'Source snapshot changed externally'
        a,b=[ROOT/f'{source}_{s}' for s in ['train_long','validation_short']]
        da,db=np.load(a/'source_crop.npz'),np.load(b/'source_crop.npz')
        assert not np.intersect1d(da['source_face_ids'],db['source_face_ids']).size
        ma,mb=[json.loads((x/'metadata.json').read_text()) for x in [a,b]]
        gap=float(np.array(ma['plan']['bounds'])[0,0]-np.array(mb['plan']['bounds'])[1,0]) if source=='zhaoqing' else float(np.array(mb['plan']['bounds'])[0,0]-np.array(ma['plan']['bounds'])[1,0])
        assert gap>0
        checks['sources'][source]={'original_archives_unchanged':hashes,'shared_original_triangles':0,'x_axis_separation_model_units':gap}
        vertices=np.load(RAW/source/'vertices.npy',mmap_mode='r');colors=np.load(RAW/source/'colors.npy',mmap_mode='r')
        rng=np.random.default_rng(713);ids=rng.choice(len(vertices),min(200000,len(vertices)),replace=False)
        fig,axes=plt.subplots(2,1,figsize=(13,8),layout='constrained',gridspec_kw={'height_ratios':[3,1]})
        for ax,dims in zip(axes,[(0,1),(0,2)]):
            ax.scatter(vertices[ids,dims[0]],vertices[ids,dims[1]],c=colors[ids]/255,s=.18,alpha=.45,rasterized=True)
            for path,meta,color,label in [(a,ma,'#168c9e','Training crop'),(b,mb,'#b64282','Validation crop')]:
                bounds=np.array(meta['plan']['bounds']);x,y=dims
                ax.add_patch(Rectangle(bounds[0,[x,y]],bounds[1,x]-bounds[0,x],bounds[1,y]-bounds[0,y],facecolor=color,alpha=.09,edgecolor=color))
                ax.add_patch(Rectangle(bounds[0,[x,y]],bounds[1,x]-bounds[0,x],bounds[1,y]-bounds[0,y],fill=False,edgecolor=color,lw=1.5))
                route=np.array(json.loads((path/'route.json').read_text())['points'])
                ax.plot(route[:,x],route[:,y],color=color,lw=2,label=label)
                ax.scatter(*route[0,[x,y]],color=color,marker='o',s=25)
                ax.scatter(*route[-1,[x,y]],color=color,marker='D',s=25)
            ax.set_aspect('equal',adjustable='datalim');ax.set_xlabel('X / unscaled model units');ax.set_ylabel(('Y' if dims[1]==1 else 'Z')+' / model units');ax.grid(alpha=.1)
        axes[0].legend(loc='upper left');axes[0].set_title(f'{source} — disjoint source regions; gap {gap:g} model units')
        fig.savefig(ROOT/f'{source}_split_overview.png',dpi=160);plt.close(fig)
    cards=[];table=[]
    for asset in manifest['assets']:
        folder=ROOT/asset['folder'];route=json.loads((folder/'route_check.json').read_text());meta=json.loads((folder/'metadata.json').read_text())
        v=np.load(folder/'source_crop.npz')['vertices'];bounds=np.array(meta['plan']['bounds'])
        assert np.all(v>=bounds[0]-1e-5) and np.all(v<=bounds[1]+1e-5)
        assert route['clearance_to_recorded_triangles_positive']
        checks['assets'][asset['folder']]=verify_glb(folder)
        checks['assets'][asset['folder']]['files']={p.name:sha(p) for p in folder.iterdir() if p.is_file() and p.suffix!='.blend1'}
        name=asset['folder'];length=route['path_length_model_units'];bound=route['surface_clearance_lower_bound']
        table.append(f'| {name} | {length:.2f} | {bound:.3f} | {asset["triangles"]:,} |')
        cards.append(f'''<article><h3>{name}</h3><p>候选路线 {length:.2f} 模型单位 · 对已重建表面的距离下界 {bound:.3f} · {asset['triangles']:,} 三角面</p>
          <div class="pair"><a href="{name}/inside_01.png"><img src="{name}/inside_01.png" loading="lazy"></a><a href="{name}/inside_02.png"><img src="{name}/inside_02.png" loading="lazy"></a></div>
          <p class="links"><a href="{name}/cave.glb">GLB（内嵌贴图）</a><a href="{name}/cave.obj">OBJ</a><a href="{name}/cave.mtl">MTL</a><a href="{name}/appearance.png">纹理 PNG</a><a href="{name}/inspection.blend">Blender 原色检查文件</a><a href="{name}/route.json">路线</a><a href="{name}/route_check.json">检查报告</a></p></article>''')
    (ROOT/'index.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>重建洞穴裁剪检查</title>
    <style>body{margin:0;background:#f4f5f7;color:#263443;font:16px/1.65 system-ui}main{max-width:1280px;margin:auto;padding:32px}h1{font-size:30px}h2{margin-top:42px}article{background:white;padding:22px;margin:24px 0;border-radius:12px}img{width:100%;display:block}.pair{display:grid;grid-template-columns:1fr 1fr;gap:12px}.links{display:flex;gap:18px;flex-wrap:wrap}a{color:#126b82}.notice{border-left:4px solid #bc8543;background:#fff6e8;padding:16px 22px}small{color:#596879}@media(max-width:700px){.pair{grid-template-columns:1fr}main{padding:16px}}</style><main>
    <h1>Metashape 重建洞穴 · 裁剪检查版</h1><p>两个来源，各一段长训练区和一段短验证区。保留原网格细节及采集颜色，空间隔离裁剪，原项目未改动。</p>
    <div class="notice"><strong>尺度未定标 · 导航就绪状态待确认</strong><br>所有长度都是模型单位，不是米。路线来自重建相机轨迹；它与已记录三角面的距离为正，但扫描缺面不能视为自由空间。黑色区域可能是缺面或裁剪边界。此版本用于检查选段和外观，不应直接作为已认证导航基准。<br>同一个真实洞穴内的长短段属于空间留出验证，不能宣称为未见洞穴 zero-shot 测试。</div>
    <h2>整体结构与空间划分</h2><p>青色为训练区，紫色为验证区；线为筛选后的候选路线，圆点为起点，菱形为终点。上下图分别为俯视与侧视。两个来源尺度未知，不能横向比较物理大小。</p>
    <a href="zhaoqing_split_overview.png"><img src="zhaoqing_split_overview.png"></a><a href="catacombs_split_overview.png"><img src="catacombs_split_overview.png"></a>
    <h2>内部视图与资产</h2><p>颜色来自原始顶点 RGB；便携贴图是对这些颜色的烘焙，不是新恢复的照片纹理或物理材质。GLB 内嵌贴图；使用 OBJ 时，请将 OBJ、MTL、PNG 放在同一个目录。OBJ 与路线为 Z-up；GLB 为 Y-up，转换为 (x,z,−y)，未缩放。</p>'''+''.join(cards)+'''<p><a href="README.md">详细说明</a> · <a href="checks.json">数据检查记录</a> · <a href="manifest.json">清单</a></p></main></html>''',encoding='utf-8')
    readme='''# Metashape spatial crops v0.1

Four **inspection-stage** assets from two real source reconstructions. Originals remain read-only. Scale is **unknown**; numeric coordinates are model units, not metres.

| Asset | Candidate path length (model units) | Distance lower bound (model units) | Triangles |
|---|---:|---:|---:|
'''+ '\n'.join(table)+'''

## What was done

- Read the active reconstructed component and its mesh/cameras directly from saved Metashape archives.
- Apply a rigid camera-up/PCA normalization (scale exactly 1). Both crops from one source share this frame; `metadata.json` records the source basis and origin.
- Clip triangles against six spatial half-spaces, interpolating vertex RGB at cut edges. No mesh deformation, simplification, hole filling or end caps.
- Training/validation regions share no original triangle IDs. Their X-axis gaps are 31 (Zhaoqing) and 6 (Catacombs) **model units**. The gap alone does not ensure independent visual statistics.
- Sample the recorded camera polyline and measure distances to cropped triangles with a BVH. Subtract half the maximum sampling interval to bound distances along the delivered sampled polyline.
- Catacombs validation's initial candidate failed this distance screening. Preserve the candidate and initial negative bound in records; retain only its longest continuous segment above the screening threshold. Do not reconnect rejected intervals. This is candidate selection, not an independent planner or a benchmark acceptance statistic.
- Encode captured vertex RGB into per-triangle texture tiles. GLB includes an unlit, double-sided material and embedded PNG; OBJ references the external PNG via MTL. No extra detail, relighting or physical material recovery is claimed. Keep GLB's linear, non-mipmapped filtering; unrelated atlas tiles can bleed under aggressive mipmaps in other importers.

## Files per region

- `cave.glb`: portable textured scan. Y-up: source normalized `(x,y,z)` becomes `(x,z,-y)`; unit calibration is still absent despite glTF's conventional unit convention.
- `cave.obj`, `cave.mtl`, `appearance.png`: use together; source normalized Z-up, same frame as routes.
- `inspection.blend`: original cropped vertex colors with the inspection camera, not the atlas representation.
- `source_crop.npz`: original-color reference with vertices, triangles, colors and original source face IDs.
- `candidate_route.json`: originally selected camera positions and transforms.
- `route.json`: delivered sampled candidate polyline. Camera ID list identifies the original candidate pool; any retained interval is recorded in `route_check.json`.
- `metadata.json`, `route_check.json`, `export_report.json`, `render_views.json`: source identity, rigid transform, crop bounds, checks, texture provenance and camera views.

## Navigation and experimental limits

These are **open, incomplete reconstructions**, not closed free-space reference meshes. Positive distance to observed triangles does not certify inside/outside, obstacle completeness, physical robot clearance, floor traversability, or policy execution. Visible black gaps remain unresolved rather than being silently filled with fabricated rock. In particular, Zhaoqing's short portion has substantial missing side coverage. A final navigation-ready release requires scale calibration, manual review of missing surfaces and an explicitly identified repaired collision copy, followed by robot-envelope checks. Preserve this unmodified-geometry reference for comparison.

Captured illumination is baked into the source colors. These are not measured albedo/PBR maps. The two region pairs are within-source spatial splits, **not four independent caves** and not an untouched real-cave zero-shot benchmark. Keep source identity in all experimental manifests; fitting priors or tuning against either source makes it development data for unseen-source claims.

## Reproduce

Run from the repository with the local Python environment:

1. `python scripts/inspect_metashape_crops.py`
2. `python scripts/crop_metashape_assets.py`
3. `blender --background --python scripts/audit_render_metashape_crops.py -- --root exports/metashape_crops_v01`
4. `python scripts/export_metashape_crops.py`
5. `python scripts/package_metashape_crops.py`

Original source locations are configured in the inspection script. Input archive hashes are recorded and rechecked during packaging. `checks.json` validates clipped bounds, source separation, GLB positions/embedded texture and OBJ counts. No original Metashape project is saved or overwritten.
'''
    (ROOT/'README.md').write_text(readme,encoding='utf-8')
    (ROOT/'checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    print('Packaged four scan crops; source, separation, geometry and texture checks passed',flush=True)


if __name__=='__main__':main()
