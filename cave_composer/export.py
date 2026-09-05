from pathlib import Path
import numpy as np


def write_obj(mesh,path,visual=False):
    path=Path(path)
    with path.open("w",encoding="utf-8",newline="\n") as f:
        f.write("# Cave Composer | metres | Z up | inward-facing free-space boundary\n")
        if visual: f.write("mtllib cave_visual.mtl\nusemtl Rock\n")
        for v in mesh.vertices: f.write("v %.7f %.7f %.7f\n"%tuple(v))
        if visual:
            # Each face selects its dominant projection. No foreign atlas/UV reuse.
            for axes in ((1,2),(0,2),(0,1)):
                for v in mesh.vertices: f.write("vt %.7f %.7f\n"%(v[axes[0]]/4,v[axes[1]]/4))
            for n in mesh.vertex_normals: f.write("vn %.7f %.7f %.7f\n"%tuple(n))
            n=len(mesh.vertices)
            for tri,normal in zip(mesh.faces,mesh.face_normals):
                projection=int(np.argmax(np.abs(normal)))
                f.write("f "+" ".join(f"{v+1}/{projection*n+v+1}/{v+1}" for v in tri)+"\n")
        else:
            for tri in mesh.faces: f.write("f %d %d %d\n"%tuple(tri+1))
    if visual:
        path.with_suffix(".mtl").write_text("newmtl Rock\nKa 0.1 0.1 0.1\nKd 1 1 1\nKs 0.04 0.04 0.04\nNs 12\nmap_Kd ../materials/rock_albedo.png\n",encoding="utf-8")
