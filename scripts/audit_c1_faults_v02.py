"""Analytic labeled geometry, separate from procedural protection ablations."""
from pathlib import Path
import sys,json
import numpy as np,trimesh
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cave_composer.delivery_validation import verify_delivered_task,sha256
from cave_composer.planning import certify_polyline

def cases():
    room=trimesh.creation.box([10,4,4]);path=[[-4,0,0],[4,0,0]]
    wall=trimesh.creation.box([.02,4,4]);cap=wall.copy();cap.apply_translation([2,0,0])
    scaled=room.copy();scaled.apply_scale([1,.2,1])
    return [
        ('clear_room',room,room,path,True,'Path x in [-4,4], y=z=0; nearest wall >=1 m, radius .55 m.'),
        ('clear_bend',room,room,[[-3,-.5,0],[0,.5,0],[3,-.5,0]],True,'Polyline inside x[-3,3], y[-.5,.5],z=0; wall distance >=1.5 m.'),
        ('thin_wall',trimesh.util.concatenate([room,wall]),trimesh.util.concatenate([room,wall]),path,False,'Solid slab |x|<=.01 spans both other axes; every straight x-crossing intersects it.'),
        ('local_cap',trimesh.util.concatenate([room,cap]),trimesh.util.concatenate([room,cap]),path,False,'Solid slab x in [1.99,2.01] intersects checked polyline.'),
        ('visual_only_wall',trimesh.util.concatenate([room,wall]),room,path,False,'Visual slab crosses path; collision reference alone would miss it.'),
        ('export_y_scale',scaled,room,path,False,'Delivered visual half-width .4 m is smaller than .55 m envelope, despite unscaled collision.')]

def main(root=Path('outputs/c1_pilot_v02/faults')):
    if root.exists():raise FileExistsError(root)
    root.mkdir(parents=True);records=[]
    for name,visual,collision,path,truth,explanation in cases():
        directory=root/name;directory.mkdir();files={}
        for kind,m in [('visual',visual),('collision',collision)]:
            files[kind]=directory/(kind+'.obj');m.export(files[kind])
        report=verify_delivered_task(files,path,.55)
        records.append({'case':name,'analytically_feasible':truth,'ground_truth_derivation':explanation,
                        'path':path,'result':report,'detected_fault':not truth and report['status']=='FAIL',
                        'false_reject':truth and report['status']=='FAIL'})
    opened=trimesh.creation.box([10,4,4]);opened.update_faces(np.arange(len(opened.faces))!=0)
    report={'ground_truth':'Analytic boxes/slabs and explicit radius inequalities fixed in source; not labels from checker.',
            'scope':'Six deterministic fixture cases; not an estimate of arbitrary-mesh detector accuracy.',
            'cases':records,'faults':sum(not r['analytically_feasible'] for r in records),
            'detections':sum(r['detected_fault'] for r in records),'false_rejects':sum(r['false_reject'] for r in records),
            'positive_controls':sum(r['analytically_feasible'] for r in records),
            'open_reference_protocol':certify_polyline(opened,[[-4,0,0],[4,0,0]],.55),
            'source_sha256':sha256(__file__)}
    (root/'results.json').write_text(json.dumps(report,indent=2));print({k:report[k] for k in ['faults','detections','false_rejects','positive_controls']})
if __name__=='__main__':main()
