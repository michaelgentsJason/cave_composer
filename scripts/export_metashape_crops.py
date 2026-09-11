"""Portable textured exports of cropped scans; no geometric simplification.

The atlas encodes captured vertex RGB, not recovered photographic detail/PBR.
Each original triangle gets a 4x4 padded affine-color tile. glTF disables
mipmapping because adjacent tiles are unrelated. Retain source_crop.npz as
the lossless geometric/color reference.
"""
import io,json,math,struct
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path('exports/metashape_crops_v01')


def linear(rgb):
    return np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)


def srgb(rgb):
    rgb=np.clip(rgb,0,1)
    return np.where(rgb<=.0031308,rgb*12.92,1.055*rgb**(1/2.4)-.055)


def export(folder):
    d=np.load(folder/'source_crop.npz');v=d['vertices'];f=d['faces'];c=linear(d['colors'])
    n=len(f);tiles=math.ceil(math.sqrt(n));size=tiles*4
    atlas=np.zeros((size,size,3),dtype=np.uint8)
    uv=np.empty((n,3,2),dtype=np.float32)
    normals=np.zeros_like(v)
    for start in range(0,n,100000):
        end=min(n,start+100000);idx=np.arange(start,end);x=(idx%tiles)*4;y=(idx//tiles)*4
        colors=c[f[start:end]]
        for dy in range(4):
            for dx in range(4):
                rgb=colors[:,0]+dx/2*(colors[:,1]-colors[:,0])+dy/2*(colors[:,2]-colors[:,0])
                atlas[y+dy,x+dx]=np.rint(srgb(rgb)*255).astype(np.uint8)
        uv[start:end,0]=np.column_stack([x+.5,y+.5])/size
        uv[start:end,1]=np.column_stack([x+2.5,y+.5])/size
        uv[start:end,2]=np.column_stack([x+.5,y+2.5])/size
        tri=v[f[start:end]];normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
        for k in range(3):np.add.at(normals,f[start:end,k],normal)
    normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-20)
    Image.fromarray(atlas).save(folder/'appearance.png')
    del atlas
    # Shared geometry vertices in OBJ, independent per-corner atlas coordinates.
    with (folder/'cave.obj').open('w',encoding='ascii',newline='\n') as out:
        out.write('# Uncalibrated model units, Z up. Captured vertex color baked to atlas.\nmtllib cave.mtl\no Cropped_scan\n')
        np.savetxt(out,v,fmt='v %.9g %.9g %.9g')
        np.savetxt(out,normals,fmt='vn %.8g %.8g %.8g')
        objuv=uv.reshape(-1,2).copy();objuv[:,1]=1-objuv[:,1]
        np.savetxt(out,objuv,fmt='vt %.9g %.9g');del objuv
        out.write('usemtl Captured_appearance\ns 1\n')
        for start in range(0,n,50000):
            fs=f[start:start+50000]+1;vt=np.arange(start*3,(start+len(fs))*3).reshape(-1,3)+1
            rows=np.stack([fs,vt,fs],axis=-1).reshape(-1,9)
            np.savetxt(out,rows,fmt='f %d/%d/%d %d/%d/%d %d/%d/%d')
    (folder/'cave.mtl').write_text('newmtl Captured_appearance\nKa 1 1 1\nKd 1 1 1\nKs 0 0 0\nd 1\nillum 0\nmap_Kd appearance.png\n',encoding='ascii')
    # glTF uses Y up. Convert explicitly, keep raw OBJ and route in source Z up.
    blob=bytearray();views=[];accessors=[]
    def append(data,target=None):
        while len(blob)%4:blob.append(0)
        view={'buffer':0,'byteOffset':len(blob),'byteLength':len(data)}
        if target:view['target']=target
        views.append(view);blob.extend(data);return len(views)-1
    def array(a,kind,bounds=False):
        entry={'bufferView':append(a.astype('<f4').tobytes(),34962),'componentType':5126,'count':len(a),'type':kind}
        if bounds:entry.update(min=a.min(0).tolist(),max=a.max(0).tolist())
        accessors.append(entry);return len(accessors)-1
    gv=v[:,[0,2,1]].copy();gv[:,2]*=-1
    gn=normals[:,[0,2,1]].copy();gn[:,2]*=-1
    attributes={'POSITION':array(gv[f].reshape(-1,3),'VEC3',True),
                'NORMAL':array(gn[f].reshape(-1,3),'VEC3'),
                'TEXCOORD_0':array(uv.reshape(-1,2),'VEC2')}
    png=(folder/'appearance.png').read_bytes();iv=append(png)
    meta={'geometry_units':'unverified_model_units','metres_per_model_unit':None,
          'appearance':'captured vertex RGB baked into per-triangle color atlas; not recovered PBR',
          'source_z_up_to_gltf_y_up':'(x,y,z) -> (x,z,-y)','source_triangles':n}
    document={'asset':{'version':'2.0','generator':'Cave Composer scan crop exporter','extras':meta},
        'extensionsUsed':['KHR_materials_unlit'],'scene':0,'scenes':[{'nodes':[0]}],
        'nodes':[{'mesh':0,'name':folder.name}],
        'meshes':[{'primitives':[{'attributes':attributes,'material':0,'mode':4}]}],
        'materials':[{'name':'Captured appearance','doubleSided':True,'extensions':{'KHR_materials_unlit':{}},
                      'pbrMetallicRoughness':{'baseColorTexture':{'index':0},'metallicFactor':0,'roughnessFactor':1}}],
        'textures':[{'sampler':0,'source':0}],
        'samplers':[{'magFilter':9729,'minFilter':9729,'wrapS':33071,'wrapT':33071}],
        'images':[{'bufferView':iv,'mimeType':'image/png'}],
        'buffers':[{'byteLength':len(blob)}],'bufferViews':views,'accessors':accessors}
    encoded=json.dumps(document,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4)
    blob.extend(b'\x00'*((-len(blob))%4))
    with (folder/'cave.glb').open('wb') as out:
        out.write(struct.pack('<4sII',b'glTF',2,12+8+len(encoded)+8+len(blob)))
        out.write(struct.pack('<I4s',len(encoded),b'JSON'));out.write(encoded)
        out.write(struct.pack('<I4s',len(blob),b'BIN\x00'));out.write(blob)
    # Independently compare atlas vertex samples against the captured colors.
    im=np.asarray(Image.open(folder/'appearance.png'));ids=np.linspace(0,n-1,min(10000,n),dtype=int)
    x=(ids%tiles)*4;y=(ids//tiles)*4
    baked=np.stack([im[y,x],im[y,x+2],im[y+2,x]],axis=1)/255
    error=float(np.max(np.abs(baked-d['colors'][f[ids]])))
    assert error<=1/255+.00001,error
    report={**meta,'texture_size':[size,size],'atlas_tile_pixels':4,'sampled_vertex_srgb_max_error':error,
        'atlas_mipmapping':False,'geometry_simplified':False,
        'obj_files':['cave.obj','cave.mtl','appearance.png'],
        'gltf_texture_embedded':True,'gltf_position_count':n*3,
        'texture_limitations':'Atlas preserves existing vertex-color detail only; use linear filtering without mipmaps to avoid unrelated-tile bleed.'}
    (folder/'export_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(folder.name,'EXPORTED',n,'triangles',size,'texture',flush=True)


if __name__=='__main__':
    for asset in json.loads((ROOT/'manifest.json').read_text())['assets']:
        export(ROOT/asset['folder'])
