"""Copy the verified paper/demo package into the Git-tracked documentation."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def publish(folder,output):
    folder,output=Path(folder).resolve(),Path(output).resolve()
    report=json.loads((folder/'verification.json').read_text())
    if report['status']!='PASS':raise ValueError('Showcase has not passed verification')
    output.mkdir(parents=True,exist_ok=True)
    for directory in ['figures','views','assets']:
        shutil.copytree(folder/directory,output/directory,dirs_exist_ok=True)
    for filename in ['index.html','source.json','validation.json','verification.json','cave_showcase.blend']:
        shutil.copy2(folder/filename,output/filename)
    readme='''# Hard 005: registered cave showcase

[![Registered hard cave overview](figures/cave_showcase.png)](figures/cave_showcase.png)

- [7200 × 3600 PNG](figures/cave_showcase.png) / [paper PDF](figures/cave_showcase.pdf)
- [Offline interactive demo](index.html): clone and open locally; GitHub displays HTML source.
- [Packed Blender scene](cave_showcase.blend): timeline frames 1–12 select cameras and inspection lights.
- [English caption](figures/caption.txt) / [LaTeX inclusion](figures/latex_include.tex)
- [12 original 1600 × 1200 renders](views/) / [camera registration](views/registered_views.json)
- [Asset manifest](assets/manifest.json) / [geometric validation](validation.json) / [delivery checks](verification.json)

Reuses hard_005 (seed 1080501): two bypass loops, two blind branches, 264.5 m of
designed passages. Adds 100 floor stones and three checkerboard props. No cave
geometry is regenerated for this delivered showcase. All images are actual
Blender Cycles renders (128 samples), using source procedural materials and
inspection lighting. The gray map is sampled from the model; yellow lines are
construction centerlines. This is not a sensor reconstruction, an executed
robot trajectory, or a calibration experiment. There is no water medium.

After asset insertion the original portal path passes checks on both final
scene meshes, with a continuous clearance lower bound of 0.589 m for a required
radius of 0.55 m. These checks apply to that path, not arbitrary navigation tasks.

For a two-column paper use the PDF at full text width; individual views are also
provided for supplementary figures. Figure text and connectors remain vectors
in the PDF; rendered images and the mesh-sampled map are raster graphics.

The full preparation/verification bundle stays under
`outputs/cave_showcase_hard_v02/`. See [reproduction instructions](../../cave_showcase_hard_v02.md).
'''
    (output/'README.md').write_text(readme,encoding='utf-8')
    checksums={p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(output.rglob('*')) if p.is_file() and p.name!='checksums.json'}
    (output/'checksums.json').write_text(json.dumps(checksums,indent=2),encoding='utf-8')
    print(json.dumps({'output':str(output),'files':len(checksums),'bytes':sum(p.stat().st_size for p in output.rglob('*') if p.is_file())}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder',default='outputs/cave_showcase_hard_v02')
    parser.add_argument('--output',default='docs/figures/showcase_hard_v02')
    args=parser.parse_args();publish(args.folder,args.output)
