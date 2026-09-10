"""Find UV-interior patch candidates; approve reviewed crops into a pinned library."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import distance_transform_edt, gaussian_filter, maximum_filter

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def glb(path):
    raw=Path(path).read_bytes();off=12;doc=None;binary=None
    while off<len(raw):
        n,t=struct.unpack_from('<II',raw,off);off+=8
        if t==0x4E4F534A:doc=json.loads(raw[off:off+n])
        elif t==0x004E4942:binary=raw[off:off+n]
        off+=n
    return doc,binary


def accessor(doc,binary,index):
    a=doc['accessors'][index];v=doc['bufferViews'][a['bufferView']]
    dtype=np.dtype({5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']])
    width={'SCALAR':1,'VEC2':2,'VEC3':3}[a['type']]
    return np.ndarray((a['count'],width),dtype=dtype,buffer=binary,
        offset=v.get('byteOffset',0)+a.get('byteOffset',0),
        strides=(v.get('byteStride',width*dtype.itemsize),dtype.itemsize)).copy()


def candidates(inventory,output):
    inventory,output=Path(inventory),Path(output);output.mkdir(parents=True,exist_ok=True)
    records=json.loads((inventory/'manifest.json').read_text())['records'];all_candidates=[]
    try:font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
    except OSError:font=ImageFont.load_default()
    for record in records:
        doc,binary=glb(record['source_glb'])
        atlas=Image.open(inventory/record['id']/record['images'][0]['file']).convert('RGB')
        w,h=atlas.size;mask=np.zeros((h,w),np.uint8)
        for mesh in doc['meshes']:
            for prim in mesh['primitives']:
                if prim.get('mode',4)!=4:continue
                uv=accessor(doc,binary,prim['attributes']['TEXCOORD_0'])
                faces=accessor(doc,binary,prim['indices']).reshape(-1,3)
                # glTF texture UV origin is at the image top-left.
                coords=np.rint(uv*[w-1,h-1]).astype(np.int32)
                for start in range(0,len(faces),20000):
                    cv2.fillPoly(mask,list(coords[faces[start:start+20000]]),255)
        rgb=np.asarray(atlas)/255.
        brightness=rgb.mean(2)
        good=(mask>0)&(brightness>.08)&(brightness<.86)&((rgb.max(2)-rgb.min(2))<.42)
        distance=distance_transform_edt(good)
        peaks=np.argwhere((distance==maximum_filter(distance,size=129))&(distance>45))
        peaks=sorted(peaks,key=lambda p:float(distance[tuple(p)]),reverse=True)
        selected=[]
        for y,x in peaks:
            half=min(256,int(distance[y,x]/np.sqrt(2)) - 10)
            if half<40 or any(np.linalg.norm(np.array([x,y])-np.array(c['center']))<180 for c in selected):continue
            patch=rgb[y-half:y+half,x-half:x+half]
            if patch.std()<.022:continue
            c={'id':record['id']+f'_patch_{len(selected):02d}','source_id':record['id'],
               'source_group':record['source_group'],'center':[int(x),int(y)],
               'crop_xywh':[int(x-half),int(y-half),int(2*half),int(2*half)],
               'uv_coverage':float((mask[y-half:y+half,x-half:x+half]>0).mean()),
               'source_image_sha256':record['images'][0]['sha256'],'attribution':record['attribution']}
            atlas.crop((x-half,y-half,x+half,y+half)).save(output/(c['id']+'.png'))
            selected.append(c)
            if len(selected)==8:break
        sheet=Image.new('RGB',(1280,680),'#f0f0f0');draw=ImageDraw.Draw(sheet)
        for i,c in enumerate(selected):
            im=Image.open(output/(c['id']+'.png'));im=im.resize((300,280))
            x=(i%4)*320+10;y=(i//4)*340+10;sheet.paste(im,(x,y))
            draw.text((x,y+285),f"{i}: {c['crop_xywh'][2]} px / UV {c['uv_coverage']:.3f}",fill='black',font=font)
        sheet.save(output/(record['id']+'_candidates.jpg'))
        all_candidates.extend(selected)
        print(record['id'],len(selected),'candidate patches',flush=True)
    (output/'candidates.json').write_text(json.dumps(all_candidates,indent=2),encoding='utf-8')


def periodic_patch(image):
    a=np.asarray(image,dtype=float)/255.;h,w,_=a.shape
    # Subtract the smooth boundary-discontinuity component using a periodic
    # Poisson solve. This is image processing, not recovered intrinsic albedo.
    v=np.zeros_like(a);v[0]=a[-1]-a[0];v[-1]=-v[0]
    v[:,0]+=a[:,-1]-a[:,0];v[:,-1]-=a[:,-1]-a[:,0]
    yy,xx=np.meshgrid(np.arange(h),np.arange(w),indexing='ij')
    denominator=2*np.cos(2*np.pi*xx/w)+2*np.cos(2*np.pi*yy/h)-4
    denominator[0,0]=1
    spectrum=np.fft.fft2(v,axes=(0,1))/denominator[:,:,None];spectrum[0,0]=0
    result=a-np.fft.ifft2(spectrum,axes=(0,1)).real
    return np.clip(result,0,1)


def approve(candidate_dir,output,ids):
    candidate_dir,output=Path(candidate_dir),Path(output);output.mkdir(parents=True,exist_ok=True)
    records={c['id']:c for c in json.loads((candidate_dir/'candidates.json').read_text())};entries=[]
    for identity in ids:
        c=records[identity];a=periodic_patch(Image.open(candidate_dir/(identity+'.png')).convert('RGB'))
        im=Image.fromarray(np.uint8(a*255))
        tile=identity+'.png';im.save(output/tile)
        entry={**c,'tile':tile,'tile_sha256':hashlib.sha256((output/tile).read_bytes()).hexdigest(),
               'review_status':'approved_rock_appearance','dimensions':list(im.size),
               'operations':['UV occupancy filtering','manual visual crop approval','periodic smooth-component removal'],
               'normal_source':'procedural, not measured','roughness_source':'configured, not measured',
               'intrinsic_albedo_recovered':False}
        entries.append(entry)
        repeat=Image.new('RGB',(im.width*2,im.height*2))
        for y in range(2):
            for x in range(2):repeat.paste(im,(x*im.width,y*im.height))
        repeat.save(output/(identity+'_repeat.png'))
    result={'schema_version':1,'kind':'reviewed_reference_texture_library','entries':entries,
        'scope':'Rock-appearance patches from scan atlases; residual capture illumination remains; not measured PBR',
        'source_role':'development_prior'}
    (output/'library.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('Library SHA256',hashlib.sha256((output/'library.json').read_bytes()).hexdigest())


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['candidates','approve'])
    p.add_argument('--inventory',default='outputs/sketchfab_texture_inventory_v01')
    p.add_argument('--candidates',default='outputs/sketchfab_texture_candidates_v01')
    p.add_argument('--output',default='materials/reference_rock_v01');p.add_argument('--ids',nargs='+')
    args=p.parse_args()
    if args.mode=='candidates':candidates(args.inventory,args.candidates)
    else:approve(args.candidates,args.output,args.ids)
