"""Spatially disjoint, color-preserving crops of the inspected saved meshes."""
import json
from pathlib import Path
import numpy as np

ROOT=Path('outputs/metashape_crops_v01')
DEST=Path('exports/metashape_crops_v01')
PLANS={
 'zhaoqing':{
  'train_long':{'bounds':[[-12,-22,-12],[84,48,16]],'camera_ids':[850,1240]},
  'validation_short':{'bounds':[[-77,26,-10],[-43,46,12]],'camera_ids':[175,365]}},
 'catacombs':{
  'train_long':{'bounds':[[-44,1,-4],[0,20,17]],'camera_ids':[136,278]},
  'validation_short':{'bounds':[[6,-9,-4],[18,7,7]],'camera_ids':[418,505]}}}


def clip(vertices,colors,faces,bounds):
    lower,upper=np.asarray(bounds)
    # Broad-phase in chunks, retaining original triangle IDs for source audits.
    keep=[];boundary=[]
    for start in range(0,len(faces),100000):
        tri=vertices[faces[start:start+100000]]
        overlap=np.all(tri.max(1)>=lower,axis=1)&np.all(tri.min(1)<=upper,axis=1)
        inside=np.all(tri.min(1)>=lower,axis=1)&np.all(tri.max(1)<=upper,axis=1)
        keep.extend((np.flatnonzero(inside)+start).tolist())
        boundary.extend((np.flatnonzero(overlap&~inside)+start).tolist())
    keep=np.asarray(keep,dtype=np.int64)
    selected=faces[keep];indices,renumber=np.unique(selected.reshape(-1),return_inverse=True)
    result_v=vertices[indices].tolist();result_c=(colors[indices].astype(float)/255).tolist()
    result_f=renumber.reshape(-1,3).tolist();source_faces=keep.tolist()
    for fi in boundary:
        polygon=[(vertices[i].astype(float),colors[i].astype(float)/255) for i in faces[fi]]
        for axis in range(3):
            for limit,sign in [(lower[axis],1),(upper[axis],-1)]:
                new=[]
                for a,b in zip(polygon,polygon[1:]+polygon[:1]):
                    da=(a[0][axis]-limit)*sign;db=(b[0][axis]-limit)*sign
                    if da>=0:new.append(a)
                    if (da>=0)!=(db>=0):
                        t=da/(da-db);p=a[0]+t*(b[0]-a[0]);p[axis]=limit
                        new.append((p,a[1]+t*(b[1]-a[1])))
                polygon=new
                if not polygon:break
            if not polygon:break
        if len(polygon)<3:continue
        n=len(result_v)
        for p,c in polygon:result_v.append(p.tolist());result_c.append(c.tolist())
        for k in range(1,len(polygon)-1):result_f.append([n,n+k,n+k+1]);source_faces.append(fi)
    v=np.asarray(result_v,dtype=np.float32);f=np.asarray(result_f,dtype=np.int32)
    tri=v[f];areas=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)
    valid=areas>1e-12
    return v,f[valid],np.asarray(result_c,dtype=np.float32),np.asarray(source_faces,dtype=np.int32)[valid]


def main():
    DEST.mkdir(exist_ok=True)
    manifest={'scale_status':'unverified_model_units','metres_per_model_unit':None,
              'split_scope':'spatially separated regions within each source cave; not unseen-cave generalization',
              'source_projects_modified':False,'assets':[]}
    for source,regions in PLANS.items():
        folder=ROOT/source
        vertices=np.load(folder/'vertices.npy',mmap_mode='r');colors=np.load(folder/'colors.npy',mmap_mode='r')
        faces=np.load(folder/'faces.npy',mmap_mode='r');inventory=json.loads((folder/'inventory.json').read_text())
        cams=np.load(folder/'camera_positions.npy');transforms=np.load(folder/'camera_transforms.npy')
        original_ids=np.array([c['id'] for c in inventory['cameras']])
        for split,plan in regions.items():
            out=DEST/(source+'_'+split);out.mkdir(exist_ok=True)
            v,f,c,fi=clip(vertices,colors,faces,plan['bounds'])
            np.savez_compressed(out/'source_crop.npz',vertices=v,faces=f,colors=c,source_face_ids=fi)
            sel=(original_ids>=plan['camera_ids'][0])&(original_ids<=plan['camera_ids'][1])
            sel&=np.all(cams>np.array(plan['bounds'][0])+.2,axis=1)&np.all(cams<np.array(plan['bounds'][1])-.2,axis=1)
            candidate={'points':cams[sel].tolist(),'camera_ids':original_ids[sel].tolist(),'transforms':transforms[sel].tolist(),
                       'source':'chronological reconstructed camera trajectory, not an independent planner'}
            (out/'candidate_route.json').write_text(json.dumps(candidate,indent=2),encoding='utf-8')
            meta={'source':source,'split':split,'plan':plan,'inventory':inventory,'triangles':len(f),'vertices':len(v),
                  'scale_status':'unverified_model_units','crop_method':'six spatial half-spaces, intersected triangles linearly clipped; no caps, smoothing or geometric filling',
                  'appearance':'original vertex colors with linear interpolation only at cut edges',
                  'physical_navigation_status':'PENDING_SCALE_AND_SCAN_COMPLETENESS'}
            (out/'metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
            manifest['assets'].append({'folder':out.name,'source':source,'split':split,'triangles':len(f)})
            print(out.name,len(f),'triangles',int(sel.sum()),'route cameras',flush=True)
    for source in PLANS:
        a,b=[DEST/(source+'_'+s) for s in ['train_long','validation_short']]
        with np.load(a/'source_crop.npz') as da,np.load(b/'source_crop.npz') as db:
            assert len(np.intersect1d(da['source_face_ids'],db['source_face_ids']))==0
    (DEST/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')


if __name__=='__main__':main()
