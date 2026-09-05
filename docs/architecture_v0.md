# Automated Cave Composer: independent architecture v0

Design recorded before implementation and before reading PLUME (2026-09-05).

## Purpose and acceptance contract

Generate controllable robot worlds in metres, with a reproducible geometric asset,
a navigation witness, separate collision/appearance representations and auditable
validation. No RL or simulator modification in this phase. A plausible render is
not evidence of traversability. Six distinct mandatory scenes must pass checks.

## Representation alternatives

| Candidate | Robotics control | Natural shape | Cost / failure mode |
|---|---|---|---|
| Swept curves / graph tubes | Exact turns and route metadata | Limited at junctions and chambers | Fast; cross-section twists, intersections and seams need repair |
| Unconstrained implicit / erosion volume | Weak topology and route control | Strong continuous morphology | Expensive rejection; blocked routes and hidden shortcuts |
| Modular scans / mesh booleans | Controllable assembly | Strong local realism | Seams, scale mismatch, licensing, large meshes; OOD leakage |
| Pure voxel cellular growth | Statistical topology control | Organic branching | Hard to prescribe bend angles and task difficulty |
| Constraint-first implicit void with semantic operations | Explicit route, turns, chambers and clearance | Shared volumetric unions plus geological fields | Grid cost, discretization error, topology must be checked |

Select **constraint-first implicit void**. The route is a geometric constraint and
ground-truth witness, not the final surface. Chambers are independently composed
lobed volumes. Geological operations act in world coordinates across junctions.
The scalar field is an occupancy level set, **not an exact signed distance**.
Clearance must therefore be measured independently on the extracted geometry.

## Pipeline

```text
structured CaveSpec / optional language adapter
  -> exact straight / circular-arc / graded route commands + semantic graph
  -> swept noncircular void + independent chamber lobes + branch / loop unions
  -> world-space stratification, fractures, asymmetric erosion, anchored rocks
  -> protect the robot swept safety envelope
  -> sample one continuous implicit field at independent mesh resolutions
  -> closed collision boundary and detailed visual boundary, normals into void
  -> independent mesh proximity + eroded occupancy connectivity validation
  -> geometry-only visibility horizon, metrics, provenance, split membership
  -> independent material assignment + Blender headless previews
  -> portable scene bundle / future simulator adapters
```

## Geometry contracts and scales

1. Semantic topology: metre-valued straight lengths, signed degree-valued turns,
   exact arc radius, slope, branches, joins, chamber locations, cross sections.
2. Navigable volume: elliptical, flattened, tall, angular and asymmetric sections
   varying continuously; closed endcaps with spawn and goal safely inset.
3. Macro geology: correlated wall variation, tilted strata / ledges, fracture
   modulation and multi-lobe chambers. These change **both** mesh fields.
4. Formations: wall/floor-attached rock ellipsoids intersect the void; the safety
   sweep takes priority. Detached loose-body dynamics are a later adapter task.
5. Fine detail: shader bump and color variations only; no claimed collision effect.
6. Material: independent appearance seed/style. No water, lighting or attenuation
   baked into albedo. Blender previews use neutral lighting to expose geometry.

The protected envelope prevents local obstruction but can broaden an infeasible
requested squeeze. Reject specs narrower than the robot diameter plus margin;
report measured widths and clearance rather than claiming nominal widths exact.
No decimation in v0: independently sampled collision surfaces preserve the field
better than unchecked decimation. Test mesh-to-path clearance at both resolutions.

## Specification and reproducibility

Versioned YAML, strict finite ranges, named presets; path command lists are the
authoritative geometry grammar. Natural-language parsing is optional and must
never silently invent unsupported semantics. Seed streams for geometry and
appearance are independent. Hash the canonical geometry config, generated mesh
arrays and output files. Byte identity is required in the same locked software
environment; no claim of cross-version floating-point identity.

## Navigation and validation

Save sampled centerlines, adjacency graph, semantic event graph, chamber records,
spawn/goals and camera frames. Validate finite vertices, nondegenerate triangles,
watertightness, winding consistency, inward normals, bounding grid margin, connected
free space, a conservative voxel robot envelope and actual mesh distance to every
route sample. Sampling spacing is included in the clearance lower bound.
Reject invalid scenes, retain diagnostic metadata, never silently label them valid.
Prevent unintended nonlocal route overlaps where possible and audit graph versus
volume topology; distinguish numerical evidence from a global geometric proof.
Marching cubes of a shared regular lattice avoids the independent-sweep triangle
intersections of mesh unions. A global robust intersection audit may remain a
declared limit; manifoldness alone is not an intersection test.

Visibility is geometric: record forward tangent-ray distance and furthest visible
route target under a configured field of view. No turbidity, backscatter or VIO
success inference. Include sampling step and range truncation.

## Split and dataset design

TRAIN / VALIDATION / ID_TEST have disjoint deterministic seed namespaces and the
same factor supports. Geometry OOD holds out angle / width / slope ranges.
Composition OOD reserves a conjunction of otherwise seen factors. Scanned realistic
OOD assets stay external and never become geometry training templates. Appearance
priors learned from eventual OOD scans constitute leakage: label exploratory priors
and do not use them for a strict untouched-real-OOD benchmark.

## Portable interface and scaling

Python library and `generate.py`, `generate_dataset.py`; no GUI dependency.
NumPy/SciPy fields, marching cubes, OBJ/MTL/PNG export, Blender background renders.
Chunk field queries to cap temporary memory; impose a maximum voxel count before
allocation. Multiprocess scene generation with per-scene atomic output and explicit
failure manifests. Rendering is optional and separate from geometry generation.
No hardcoded workstation paths in reusable code; Blender supplied by flag or PATH.
Dense grids establish v0; sparse bricks / VDB are a future scaling substitution.

## Environment and scope

The requested Linux `/media/hong/Ubun_Shared/Composer` path is not a Windows path;
check WSL separately and record availability. Workspace initially empty; Blender
desktop shortcut resolves to `D:/Blender`. Asset discovery is read-only and does
not copy source geometry. If no licensed scan materials are available, implement
the material-prior interface and report the transfer experiment as unavailable.

Stonefish adapter research and PLUME comparison occur after the independent
prototype. Simulator readiness is not runtime validation until a Stonefish load
and collision/navigation smoke test has actually executed.
