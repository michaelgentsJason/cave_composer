"""Read saved Metashape archives without opening or mutating the source project."""
from pathlib import Path
import hashlib,json,zipfile,xml.etree.ElementTree as ET
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SOURCES={
 'zhaoqing':r'D:\Desktop\Cave_scan\zhaoqing_metashape\native_live_record_room_native_20260828-162520\metashape\insight_outside.files',
 'catacombs':r'D:\Desktop\Catacombs_Visual-Inertial_Data\Metashape_RGB_1fps_v3\002.files'}
ROOT=Path('outputs/metashape_crops_v01')


def inspect(name,source):
    source=Path(source);out=ROOT/name;out.mkdir(parents=True,exist_ok=True)
    model=source/'0/0/model/model.zip';chunk=source/'0/chunk.zip';frame=source/'0/0/frame.zip'
    with zipfile.ZipFile(model) as z:
        raw=z.read('mesh.ply');doc=ET.fromstring(z.read('doc.xml'))
    end=raw.index(b'end_header')+len(b'end_header')
    while raw[end:end+1] in [b'\r',b'\n']:end+=1
    header=raw[:end].decode();nv=int(doc.findtext('mesh/vertexCount'));nf=int(doc.findtext('mesh/faceCount'))
    vtype=np.dtype([('xyz','<f4',3),('rgb','u1',3),('confidence','<f4')])
    vertices=np.frombuffer(raw,dtype=vtype,count=nv,offset=end)
    has_uv=doc.findtext('mesh/hasUV')=='true'
    ftype=np.dtype([('count','u1'),('indices','<i4',3)]+([('uvcount','u1'),('uv','<f4',6)] if has_uv else []))
    faces=np.frombuffer(raw,dtype=ftype,count=nf,offset=end+nv*vtype.itemsize)
    assert len(raw)==end+nv*vtype.itemsize+nf*ftype.itemsize
    assert np.all(faces['count']==3)
    with zipfile.ZipFile(chunk) as z:tree=ET.fromstring(z.read('doc.xml'))
    active=tree.find('components').get('active_id');cameras=[]
    for c in tree.findall('cameras/camera'):
        if c.get('component_id')!=active or c.find('transform') is None:continue
        transform=np.fromstring(c.findtext('transform'),sep=' ').reshape(4,4)
        cameras.append({'id':int(c.get('id')),'label':c.get('label'),'transform':transform.tolist()})
    cameras.sort(key=lambda c:c['id'])
    transforms=np.array([c['transform'] for c in cameras]);positions=transforms[:,:3,3]
    up=np.median(-transforms[:,:3,1],axis=0);up/=np.linalg.norm(up)
    center=np.median(positions,axis=0);flat=positions-center
    flat-=np.outer(flat@up,up)
    _,_,vt=np.linalg.svd(flat,full_matrices=False);forward=vt[0]
    if (positions[-1]-positions[0])@forward<0:forward=-forward
    side=np.cross(up,forward);side/=np.linalg.norm(side);forward=np.cross(side,up)
    basis=np.column_stack([forward,side,up])
    xyz=(vertices['xyz'].astype(float)-center)@basis
    normalized=(positions-center)@basis
    np.save(out/'vertices.npy',xyz.astype('float32'));np.save(out/'colors.npy',vertices['rgb'])
    np.save(out/'faces.npy',faces['indices']);np.save(out/'camera_positions.npy',normalized)
    newtransforms=transforms.copy();newtransforms[:,:3,:3]=np.einsum('ij,njk->nik',basis.T,transforms[:,:3,:3]);newtransforms[:,:3,3]=normalized
    np.save(out/'camera_transforms.npy',newtransforms)
    meta={'source':str(source),'vertices':nv,'faces':nf,'saved_uv':has_uv,
          'appearance':'saved vertex RGB; no texture image found in model archive',
          'scale_status':'unverified_model_units','metres_per_model_unit':None,'active_component':active,
          'normalization':{'source_origin':center.tolist(),'source_basis_columns':basis.tolist(),'scale':1.,'method':'rigid camera-up + horizontal PCA frame'},
          'source_hashes':{str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [model,chunk,frame]},
          'cameras':[{'id':c['id'],'label':c['label']} for c in cameras],
          'bounds':np.array([xyz.min(0),xyz.max(0)]).tolist()}
    (out/'inventory.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    rng=np.random.default_rng(713);idx=rng.choice(nv,min(150000,nv),replace=False)
    with plt.rc_context({'font.size':11}):
        fig,axes=plt.subplots(2,1,figsize=(14,9),layout='constrained')
        for ax,dims in zip(axes,[(0,1),(0,2)]):
            ax.scatter(xyz[idx,dims[0]],xyz[idx,dims[1]],c=vertices['rgb'][idx]/255.,s=.2,alpha=.5,rasterized=True)
            ax.plot(normalized[:,dims[0]],normalized[:,dims[1]],color='#b64282',lw=.8)
            for i in np.linspace(0,len(cameras)-1,15,dtype=int):ax.annotate(str(cameras[i]['id']),normalized[i,list(dims)],fontsize=8,color='red')
            ax.set(aspect='equal',xlabel='X / unscaled model units',ylabel=('Y' if dims[1]==1 else 'Z')+' / model units')
        fig.suptitle(name+' / saved mesh + active-component cameras');fig.savefig(out/'source_overview.png',dpi=150);plt.close(fig)
    print(name,'camera count',len(cameras),'bounds',meta['bounds'],'camera x quantiles',np.quantile(normalized[:,0],[0,.2,.5,.7,.8,1]).tolist(),flush=True)


if __name__=='__main__':
    for name,source in SOURCES.items():inspect(name,source)
