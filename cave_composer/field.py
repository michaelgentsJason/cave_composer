"""Continuous positive-inside void field; explicitly not a true signed distance."""
import numpy as np
from scipy.spatial import cKDTree
from scipy import ndimage
from skimage.measure import marching_cubes
import trimesh


class CaveField:
    def __init__(self, spec, routes, seed):
        self.spec, self.routes = spec, routes
        rng = np.random.default_rng(np.random.SeedSequence([int(seed), 17]))
        self.phase = rng.uniform(-np.pi, np.pi, 12)
        starts, ends, widths, heights, ss, exponents, asymmetries = [], [], [], [], [], [], []
        for r in routes:
            starts.extend(r["points"][:-1]); ends.extend(r["points"][1:])
            arc = (r["s"][:-1] + r["s"][1:])/2
            variation = spec["corridor"]["variation"]
            w = (r["widths"][:-1]+r["widths"][1:])/4
            h = (r["heights"][:-1]+r["heights"][1:])/4
            w *= 1 + variation*(0.62*np.sin(arc*0.31+self.phase[0]) + 0.38*np.sin(arc*0.77+self.phase[1]))
            h *= 1 + variation*(0.6*np.sin(arc*0.27+self.phase[2]) + 0.4*np.sin(arc*0.63+self.phase[3]))
            widths.extend(w); heights.extend(h); ss.extend(arc)
            for sect in r["sections"][:-1]:
                exponents.append({"oval":2,"elliptical":2,"flattened":3.2,"tall":2.3,"triangular":1.3,"asymmetric":2.5,"fracture":1.35,"irregular":2.5}[sect])
                asymmetries.append({"oval":0,"elliptical":0,"flattened":0.08,"tall":0.1,"triangular":0.22,"asymmetric":0.24,"fracture":0.28,"irregular":0.17}[sect])
        self.a, self.b = np.asarray(starts), np.asarray(ends)
        d = self.b-self.a
        self.lengths = np.linalg.norm(d, axis=1)
        self.tangent = d/self.lengths[:,None]
        self.side = np.cross(np.tile([0.,0.,1.], (len(d),1)), self.tangent)
        self.side /= np.linalg.norm(self.side, axis=1)[:,None]
        self.up = np.cross(self.tangent, self.side)
        self.w, self.h, self.s = np.asarray(widths), np.asarray(heights), np.asarray(ss)
        self.power, self.asym = np.asarray(exponents), np.asarray(asymmetries)
        self.tree = cKDTree((self.a+self.b)/2)
        self.safety = spec["robot"]["radius"]+spec["robot"]["margin"]
        # Additional voxel discretization allowance is separate from the requested safety margin.
        self.protected_radius = self.safety + spec["mesh"]["collision_voxel"]*2.1
        self.lobes, self.chamber_records = [], []
        main = routes[0]
        for ci, ch in enumerate(spec["chambers"]):
            idx = int(round(ch["at"]*(len(main["points"])-1)))
            center = main["points"][idx]
            radii = np.asarray(ch["radii"], dtype=float)
            self.lobes.append((center, radii))
            for _ in range(int(ch.get("lobes", 5))):
                delta = rng.normal(size=3); delta /= np.linalg.norm(delta)
                offset = delta*radii*rng.uniform(0.35, 0.7)
                self.lobes.append((center+offset, radii*rng.uniform(0.5, 0.8, 3)))
            self.chamber_records.append({"id": ci, "at": ch["at"], "position": center.tolist(), "radii": radii.tolist(), "lobes": int(ch.get("lobes",5))+1, "style": ch.get("style","irregular")})
        self.rocks = []
        for _ in range(int(spec["geology"]["formations"])):
            idx = int(rng.integers(3, max(4,len(self.a)-3)))
            floor = rng.random() < 0.6
            if floor:
                center = (self.a[idx]+self.b[idx])/2 - self.up[idx]*self.h[idx]*rng.uniform(0.85,1.04) + self.side[idx]*self.w[idx]*rng.uniform(-0.6,0.6)
            else:
                center = (self.a[idx]+self.b[idx])/2 + self.side[idx]*self.w[idx]*rng.choice([-0.97,0.97])
            self.rocks.append((center, rng.uniform([0.45,0.45,0.4], [1.25,1.2,1.1])))
        pad = np.maximum(self.w.max(), self.h.max()) + spec["geology"]["amplitude"]*3+2
        lower = np.minimum(self.a.min(0), self.b.min(0))-pad
        upper = np.maximum(self.a.max(0), self.b.max(0))+pad
        for center, radii in self.lobes:
            lower = np.minimum(lower, center-radii-2)
            upper = np.maximum(upper, center+radii+2)
        self.bounds = np.array([lower, upper])

    def __call__(self, points):
        points = np.asarray(points, dtype=float).reshape(-1,3)
        out = np.empty(len(points), dtype=np.float32)
        for start in range(0,len(points),24000):
            q = points[start:start+24000]
            _, idx = self.tree.query(q, k=min(8,len(self.a)))
            if idx.ndim == 1: idx = idx[:,None]
            rel = q[:,None,:]-self.a[idx]
            t = np.einsum("nkj,nkj->nk",rel,self.tangent[idx])
            tclip = np.clip(t, 0, self.lengths[idx])
            delta = rel - tclip[:,:,None]*self.tangent[idx]
            u = np.einsum("nkj,nkj->nk",delta,self.side[idx])
            v = np.einsum("nkj,nkj->nk",delta,self.up[idx])
            enddist = t-tclip
            p = self.power[idx]
            tilt = self.asym[idx]*v
            w = self.w[idx]*(1 + self.asym[idx]*0.4*np.tanh(v))
            rho = (np.abs((u+tilt)/w)**p + np.abs(v/self.h[idx])**p + np.abs(enddist/np.minimum(w,self.h[idx]))**p)**(1/p)
            base = np.max((1-rho)*np.minimum(w,self.h[idx]),axis=1)
            distance = np.sqrt(np.min(np.sum(delta*delta,axis=2),axis=1))
            for center, radii in self.lobes:
                ell = (1-np.sqrt(np.sum(((q-center)/radii)**2,axis=1)))*radii.min()
                base = np.maximum(base,ell)
            x,y,z = q.T
            ph = self.phase
            # Tilted bedding creates continuous shelves across branches; two erosion scales
            # create broad dissolution pockets and sharper fractured rock relief.
            macro = (0.48*np.sin(x*0.71+y*0.37+ph[4])*np.cos(z*0.91-y*0.18+ph[5])
                     +0.30*np.sin(y*1.61+z*0.77+ph[6])*np.cos(x*1.17+ph[7])
                     +0.16*np.sin(x*3.7-y*2.8+z*1.8+ph[8]))
            bedding = np.tanh(3*np.sin(z*4.1+x*0.23+y*0.11+ph[9]))
            fracture = np.exp(-(np.sin(x*0.63-y*0.47+z*0.2+ph[10])/0.14)**2)
            f = base + self.spec["geology"]["amplitude"]*(macro+0.22*fracture) + self.spec["geology"]["strata"]*bedding
            for center,radii in self.rocks:
                rock = (np.sum(np.abs((q-center)/radii)**1.65,axis=1)**(1/1.65)-1)*radii.min()
                rock += 0.065*np.sin(x*5.1+y*3.7)*np.sin(z*4.2-x*1.8)
                f = np.minimum(f,rock)
            f = np.maximum(f, self.protected_radius-distance)
            out[start:start+len(q)] = f
        return out

    def grid(self, voxel):
        origin = np.floor(self.bounds[0]/voxel)*voxel
        shape = np.ceil((self.bounds[1]-origin)/voxel).astype(int)+1
        count = int(np.prod(shape))
        if count > self.spec["mesh"]["max_voxels"]:
            raise ValueError(f"Grid requires {count:,} voxels, exceeding configured maximum; increase voxel size or use a shorter cave")
        data = np.empty(tuple(shape),dtype=np.float32)
        yz = np.stack(np.meshgrid(np.arange(shape[1]),np.arange(shape[2]),indexing="ij"),axis=-1).reshape(-1,2)
        for i in range(shape[0]):
            q = np.column_stack([np.full(len(yz),i),yz])*voxel+origin
            data[i] = self(q).reshape(shape[1:])
        return data, origin

    def mesh(self, voxel):
        data, origin = self.grid(voxel)
        faces_boundary = [data[0],data[-1],data[:,0],data[:,-1],data[:,:,0],data[:,:,-1]]
        if any(np.any(a>=0) for a in faces_boundary):
            raise ValueError("Void touches grid boundary; cannot emit a sealed cave")
        labels,count=ndimage.label(data>0)
        anchor=np.rint((self.routes[0]['points'][0]-origin)/voxel).astype(int)
        component=labels[tuple(anchor)]
        if component==0: raise ValueError('Route starts outside the sampled void')
        stray=(labels>0)&(labels!=component)
        removed=int(stray.sum())
        if removed>max(20,0.01*np.count_nonzero(data>0)):
            raise ValueError('Large disconnected free-space component; reject rather than discard intended geometry')
        data[stray]=-np.abs(data[stray])-voxel*0.01
        # Keep isosurface intersections away from lattice corners to avoid
        # arbitrarily tiny triangles due to near-zero floating point samples.
        near=np.abs(data)<voxel*0.001
        data[near]=np.where(data[near]>=0,1,-1)*voxel*0.001
        if not hasattr(self,'repairs'): self.repairs={}
        self.repairs[str(voxel)]={'removed_isolated_void_voxels':removed,'components_before':int(count),'method':'retain start-connected void; reject if discarded volume exceeds 1 percent'}
        v,f,_,_ = marching_cubes(data,0,spacing=(voxel,)*3,allow_degenerate=False,method="lewiner")
        mesh = trimesh.Trimesh(vertices=v+origin,faces=f,process=True)
        # A cave surface faces the free void, so its signed enclosed volume is negative.
        if mesh.volume > 0: mesh.invert()
        return mesh, data, origin
