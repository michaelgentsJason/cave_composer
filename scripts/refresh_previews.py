"""Refresh bundle presentation and hashes without regenerating or editing geometry."""
import sys,json,argparse,subprocess,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from cave_composer.routes import junction_graph
from cave_composer.previews import topology_preview
from cave_composer.pipeline import dump

p=argparse.ArgumentParser(); p.add_argument('scenes',nargs='+'); p.add_argument('--blender'); a=p.parse_args()
for scene in a.scenes:
    folder=Path(scene).resolve(); graph=json.loads((folder/'navigation/navigation_graph.json').read_text())
    dump(folder/'navigation/junction_graph.json',junction_graph(graph))
    nav=json.loads((folder/'navigation/centerline.json').read_text()); routes=[]
    for r in nav['routes']: routes.append({**r,'points':np.asarray(r['points']),'s':np.asarray(r['s_metres'])})
    visibility=json.loads((folder/'navigation/visibility_horizon.json').read_text())
    topology_preview(routes,graph,visibility,folder/'previews',folder.name)
    if a.blender:
        with (folder/'metadata/render_refresh.log').open('w') as log:
            subprocess.run([a.blender,'--background','--python',str(Path(__file__).resolve().parents[1]/'cave_composer/blender_render.py'),'--','--scene',str(folder),'--save-blend'],stdout=log,stderr=subprocess.STDOUT,check=True)
    files={str(f.relative_to(folder)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(folder.rglob('*')) if f.is_file() and f.name!='checksums.json'}
    dump(folder/'metadata/checksums.json',files)
    print(folder.name,'refreshed',flush=True)
