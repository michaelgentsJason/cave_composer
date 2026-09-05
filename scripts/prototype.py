"""Independent A/B/C geometry milestone; superseded by the full scene CLI."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse
import time
import json
import numpy as np
from cave_composer.spec import load_spec
from cave_composer.routes import build_routes
from cave_composer.field import CaveField
from cave_composer.materials import write_material

p=argparse.ArgumentParser(); p.add_argument("configs",nargs="+"); args=p.parse_args()
for cfg in args.configs:
    start=time.perf_counter(); s=load_spec(cfg); routes=build_routes(s); field=CaveField(s,routes,42)
    out=Path("outputs/prototype")/s["name"]; out.mkdir(parents=True,exist_ok=True)
    mesh,_,_=field.mesh(s["mesh"]["visual_voxel"])
    np.savez_compressed(out/"mesh.npz",vertices=mesh.vertices,faces=mesh.faces)
    write_material(s["material"],out/"materials")
    info={"name":s["name"],"points":routes[0]["points"].tolist(),"bounds":mesh.bounds.tolist(),"faces":len(mesh.faces),"watertight":mesh.is_watertight,"winding_consistent":mesh.is_winding_consistent,"seconds":time.perf_counter()-start}
    (out/"prototype.json").write_text(json.dumps(info,indent=2))
    print(json.dumps({k:v for k,v in info.items() if k not in ('points','bounds')}),flush=True)
