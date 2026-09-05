"""Re-run geometry validation with explicit source and mesh identity evidence."""
import sys,argparse,json,hashlib,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import trimesh
from cave_composer.spec import load_spec
from cave_composer.routes import build_routes,navigation_graph
from cave_composer.field import CaveField
from cave_composer.validation import validate
from cave_composer.pipeline import dump,mesh_digest

p=argparse.ArgumentParser(); p.add_argument('scenes',nargs='+'); a=p.parse_args()
failed=False
for scene in a.scenes:
    folder=Path(scene); spec=load_spec(folder/'metadata/config.yaml'); provenance=json.loads((folder/'metadata/provenance.json').read_text())
    routes=build_routes(spec); field=CaveField(spec,routes,provenance['seed']); graph=navigation_graph(routes,field.chamber_records,spec['bottlenecks'])
    meshes={}
    for k in ['visual','collision']:
        data=np.load(folder/k/'mesh.npz'); meshes[k]=trimesh.Trimesh(data['vertices'],data['faces'],process=False)
        if mesh_digest(meshes[k])!=provenance[k+'_mesh_sha256']: raise RuntimeError('Stored mesh hash mismatch')
    regenerated,grid,origin=field.mesh(spec['mesh']['collision_voxel'])
    if mesh_digest(regenerated)!=provenance['collision_mesh_sha256']: raise RuntimeError('Current generator no longer reproduces this bundle; regenerate it')
    report,_=validate(spec,routes,graph,field,meshes['visual'],meshes['collision'],grid,origin)
    report['revalidation']={'mesh_sha256_verified':True,'collision_regenerated_identically':True,'validator_source_sha256':hashlib.sha256((Path(__file__).resolve().parents[1]/'cave_composer/validation.py').read_bytes()).hexdigest()}
    audit=folder/'metadata/intersection_audit.json'
    if audit.exists():
        report['intersection_audit']=json.loads(audit.read_text()); report['checks']['bvh_no_nonadjacent_intersections']=report['intersection_audit']['status']=='PASS'
        if not report['checks']['bvh_no_nonadjacent_intersections']: report['status']='INVALID'
    dump(folder/'metadata/validation.json',report)
    metrics=json.loads((folder/'metadata/metrics.json').read_text()); metrics['validation']=report['status']; dump(folder/'metadata/metrics.json',metrics)
    print(folder.name,report['status'],[k for k,v in report['checks'].items() if not v],flush=True)
    failed|=report['status']!='VALID'
raise SystemExit(2 if failed else 0)
