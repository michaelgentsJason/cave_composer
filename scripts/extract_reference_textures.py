"""Extract embedded GLB images without loading or changing scan geometry.

This inventories capture textures, not recovered PBR materials or tileable maps.
"""
import argparse
import hashlib
import html
import io
import json
from pathlib import Path
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cave_composer.materials import infer_image_prior, write_material


def extract(source,output):
    source,output=Path(source).resolve(),Path(output).resolve()
    output.mkdir(parents=True,exist_ok=True)
    records=[]
    for path in sorted(source.glob('*.glb')):
        raw=path.read_bytes()
        if len(raw)<20:raise ValueError(f'Truncated GLB: {path}')
        magic,version,total=struct.unpack_from('<4sII',raw)
        if magic!=b'glTF' or version!=2 or total!=len(raw):raise ValueError(f'Invalid GLB header: {path}')
        offset=12;document=None;binary=None
        while offset<len(raw):
            length,kind=struct.unpack_from('<II',raw,offset);offset+=8
            if offset+length>len(raw):raise ValueError('Invalid GLB chunk range')
            chunk=raw[offset:offset+length];offset+=length
            if kind==0x4E4F534A:document=json.loads(chunk)
            elif kind==0x004E4942:binary=chunk
        if document is None or binary is None:raise ValueError('Expected JSON and BIN chunks')
        directory=output/path.stem;directory.mkdir(exist_ok=True)
        extras=document.get('asset',{}).get('extras',{})
        channels={i:[] for i in range(len(document.get('images',[])))}
        materials=document.get('materials',[])
        for mid,mat in enumerate(materials):
            pbr=mat.get('pbrMetallicRoughness',{})
            for channel,slot in [('base_color',pbr.get('baseColorTexture')),('metallic_roughness',pbr.get('metallicRoughnessTexture')),
                                 ('normal',mat.get('normalTexture')),('occlusion',mat.get('occlusionTexture')),('emissive',mat.get('emissiveTexture'))]:
                if slot is not None:
                    texture=document['textures'][slot['index']]
                    if 'source' in texture:channels[texture['source']].append({'material':mid,'channel':channel})
        images=[]
        for index,im in enumerate(document.get('images',[])):
            if 'bufferView' not in im:raise ValueError('Only embedded bufferView images are supported')
            view=document['bufferViews'][im['bufferView']]
            if view.get('buffer',0)!=0:raise ValueError('External buffers are not supported')
            begin=view.get('byteOffset',0);end=begin+view['byteLength']
            if not 0<=begin<end<=len(binary):raise ValueError('Image bufferView out of range')
            payload=binary[begin:end]
            extension={'image/jpeg':'.jpg','image/png':'.png'}.get(im['mimeType'])
            if extension is None:raise ValueError('Unsupported image MIME type')
            name=f'image_{index:02d}{extension}';target=directory/name
            target.write_bytes(payload)
            with Image.open(io.BytesIO(payload)) as image:
                dimensions=list(image.size)
                preview=image.convert('RGB');preview.thumbnail((768,768))
                preview.save(directory/f'preview_{index:02d}.jpg',quality=92)
                image.verify()
            item={'file':name,'dimensions':dimensions,'sha256':hashlib.sha256(payload).hexdigest(),
                  'channels':channels[index],'extracted_bytes_unchanged':target.read_bytes()==payload}
            # Draft color statistics only. This deliberately does not claim UV
            # island masking, rock-region selection, intrinsic albedo or tiling.
            if any(c['channel']=='base_color' for c in channels[index]):
                prior=infer_image_prior(target,directory/f'palette_{index:02d}.json')
                settings={k:prior[k] for k in ['style','palette','seed','roughness','prior_source']}
                settings['style']='limestone'
                write_material(settings,directory/f'palette_preview_{index:02d}')
                item['palette_status']='DRAFT: whole-atlas color quantiles; includes capture lighting, non-rock surfaces and padding'
            images.append(item)
        group='font_del_truffe' if path.stem.startswith('font_del_truffe') else 'porth_yr_ogof' if path.stem.startswith('porth_yr_ogof') else path.stem
        record={'id':path.stem,'source_glb':str(path),'source_glb_sha256':hashlib.sha256(raw).hexdigest(),
            'source_group':group,'group_basis':'Conservative grouping from embedded model titles; not independent environments per file',
            'attribution':extras,'materials':materials,'images':images,
            'unlit':any('KHR_materials_unlit' in m.get('extensions',{}) for m in materials),
            'role':'development_texture_candidate','used_for_training':False,'tileable_verified':False,
            'limitations':['Captured RGB is not intrinsic albedo','UV atlas belongs to original mesh',
                           'No normals/roughness recovered','Raw atlas is not approved for direct tiling on generated caves']}
        (directory/'manifest.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
        (directory/'ATTRIBUTION.txt').write_text(f"{extras.get('title',path.stem)}\n{extras.get('author','Unknown author')}\n"
            f"Source: {extras.get('source','Unknown')}\nLicense (embedded metadata): {extras.get('license','Unknown')}\n"
            'Original embedded image bytes extracted unchanged. Previews resized; draft procedural palettes derived from observed RGB.\n',encoding='utf-8')
        records.append(record)
        print(path.name,[(i['dimensions'],i['channels']) for i in images],flush=True)
    if not records:raise ValueError('No GLB files found')
    report={'schema_version':1,'status':'EXTRACTED_NOT_TRAINING_INTEGRATED','models':len(records),
        'images':sum(len(r['images']) for r in records),'conservative_source_groups':len({r['source_group'] for r in records}),
        'records':records}
    (output/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    cards=[]
    for r in records:
        for i,im in enumerate(r['images']):
            base=r['id'];attrib=r['attribution']
            cards.append(f'<article><h2>{html.escape(attrib.get("title",base))}</h2><p>{im["dimensions"][0]} × {im["dimensions"][1]} · unlit: {r["unlit"]}</p>'
                f'<a href="{base}/{im["file"]}"><img src="{base}/preview_{i:02d}.jpg" alt="原始UV图集预览"></a>'
                f'<p>粗略颜色统计 → 程序化预览（不是原始纹理迁移）</p><img class="palette" src="{base}/palette_preview_{i:02d}/rock_albedo.png" alt="颜色先验草稿">'
                f'<p>{html.escape(attrib.get("author",""))} · <a href="{html.escape(attrib.get("source",""),quote=True)}">来源</a> · <a href="{base}/ATTRIBUTION.txt">署名与许可</a></p></article>')
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Cave Composer · Reference texture inventory</title><style>
body{font-family:Arial,"Microsoft YaHei",sans-serif;background:#f2f3f4;color:#24303b;margin:30px auto;padding:0 22px;max-width:1400px}h1{font-size:28px}h2{font-size:18px}p{line-height:1.6}main{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}article{background:white;padding:20px;border-radius:8px}img{width:100%;max-height:460px;object-fit:contain;background:#161616}.palette{height:130px;object-fit:cover}a{color:#16758a}@media(max-width:700px){main{grid-template-columns:1fr}}</style>
<h1>Sketchfab 洞穴纹理检查</h1><p>提取的是原模型的 UV 图集，不是可直接平铺的 PBR 材质。下方色板仅是未筛选岩壁区域的颜色统计草稿。4 个模型按名称保守归为 2 个洞穴来源；尚未接入训练或修改现有 30 套资产。</p><main>'''+''.join(cards)+'</main></html>'
    (output/'index.html').write_text(page,encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',default='sketchfab_caves')
    parser.add_argument('--output',default='outputs/sketchfab_texture_inventory_v01')
    args=parser.parse_args();extract(args.source,args.output)
