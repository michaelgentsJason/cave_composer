# Structural irregularity: implementation audit and first controlled comparison

## Outcome and claim boundary

Four independently controlled morphology modules are now implemented. The
[comparison gallery](../exports/morphology_v01/index.html) provides matched
textured and untextured renders, actual mesh sections, portable GLB/OBJ assets,
and validation records. Both full cases and four single-module cases passed
generation validation. This demonstrates controllable changes in geometry while
retaining checked navigability. **A reduction in distance to a real-cave geometry
distribution has not been measured.**

## Audit: where the tube-like bias came from

1. `field.py` unions segment-local superelliptic profiles with a small fixed
   catalogue of powers and asymmetries. Width and height modulation mostly used
   the same two sinusoidal scales everywhere. A label such as `irregular` did
   not represent arbitrarily changing nonconvex sections or a shifted cavity
   centroid. Chambers were unions of ellipsoidal lobes.
2. The rock field already had several spatial frequencies, bedding and fracture
   bands. Their amplitudes were almost stationary over a scene. More amplitude
   would produce more relief at the same frequencies, not distinct morphological
   regions, ledges, localized obstruction events or side cavities.
3. `formations` scattered similarly scaled floor/wall primitives without named
   clusters, explicit locations or independent controls for overhangs, roof
   changes and wall intrusions. Their individual contributions were difficult
   to ablate.
4. Existing route commands support cubic 3D curves, circular compound turns,
   grades, branches, loops, dead ends, chambers and bottlenecks. These capabilities
   are not absent; sampler coverage and geometry coupling need improvement.
   The present paired experiment holds the existing easy route fixed so these
   effects do not confound the cross-section and obstacle changes.
5. The last field operation restores a constant protected tube around construction
   routes. This is useful for generation reliability but imposes a strong
   morphological lower bound: sufficiently intrusive rocks are clipped away.
   Noise alone cannot remove that bias while retaining the same protection rule.
6. Visual voxels at 0.20 m and collision voxels at 0.34 m in this example do not
   resolve fine cracks. A normal map is appearance, not collision geometry.

Real caves need not always be highly irregular. Passage shape depends on
formation context, so "more roughness" is not a universal realism objective.
Morphological diversity and formation context are illustrated in the
[NSS passage reference](https://caves.org/virtualcave/passage-types/); measured
large depth-dependent geometry transitions are also reported for the
[Sansha Yongle Blue Hole](https://www.nature.com/articles/s41598-018-35220-x).
These references motivate conditioning and measurement; they do not validate
our generated distribution or supply fitted parameters.

## First-round priorities, controls and cost

| Priority | Implemented module | Parameters | Purpose / engineering scope |
|---|---|---|---|
| 1 | Along-route cross-section deformation | `cross_section.amplitude`, `eccentricity`, `length_scale` | Low-order angular lobes, moving cavity offset and rotation; medium cost; addresses fixed convex profiles |
| 2 | Local structure events | `features`: `ceiling_drop`, `floor_rise`, `wall_intrusion`, `overhang`, `side_cavity` | Route-frame positive/negative superellipsoids; medium cost; localized clearance transitions and hidden pockets |
| 3 | Rockfall clusters | Feature kind `rockfall`, plus `count` | Seeded angular rock groups near the floor; low incremental cost; explicit clutter regions rather than global counts |
| 4 | Nonstationary roughness envelope | `roughness.contrast`, `length_scale` | Continuous world-space modulation of the existing relief amplitude; low cost; avoids nearest-route discontinuities at junctions |
| 5 | Next: real-reference calibration and coverage | Scale-aware section/visibility distributions; joint-controlled 3D route families | Highest next value for the paper's distribution-gap claim; not implemented as a fitted model in this round |

All controls live under the optional top-level `morphology` key. Omit it for
the old generator. Cross-section amplitude is in [0, 0.4], eccentricity in
[0, 0.3] of local half-dimensions, roughness contrast in [0, 1], and length scales
in [2, 40] metres. Zero amplitudes/contrast disable their effects. The first
three metres at route ends taper section deformation to preserve portal context.

Each feature has a unique `id`, `kind`, optional `route` (default `main`), `at`
(route arclength fraction), `length`, `span`, `depth` in metres, optional `side`
(-1 or +1), and `strength` in [0, 1]. Rockfall also accepts integer `count`.
`strength: 0` disables a feature. Geometry and appearance use separate seeds;
rockfall randomness depends on its stable feature ID, not list order or the
other modules. Sampled parameters and actual primitive positions are saved in
`metadata/morphology.json` and covered by bundle checksums.

`side_cavity` adds a local void pocket, not a navigation-graph branch. Robot entry
into each pocket is not guaranteed. Rockfall primitives can merge with the floor,
with one another, or be clipped by protection; this implementation does not promise
a requested number of isolated final boulders. Roof/ledge primitives are geometric
approximations, not simulated collapse or erosion.

## Controlled evidence from this run

All six paired configurations use geometry seed **97001**, material seed **97011**,
the same 50.38 m route with two gentle bends, identical mesh resolutions and the
same reference texture. The two exported cases also have identical camera poses,
lights and render settings; the clay material removes color and normal maps.

| Final-mesh diagnostic | Before | After |
|---|---:|---:|
| Section area coefficient of variation | 0.0660 | 0.1319 |
| Mean nonconvexity, `1 − area / convex-hull area` | 0.0320 | 0.1265 |
| Mean centroid offset / equivalent-circle radius | 0.0265 | 0.1787 |
| Maximum sampled area gradient, m²/m | 2.088 | 6.515 |
| Mean continuously visible route length, m | 22.022 | 17.496 |
| Independent path collision-mesh clearance bound, m | 1.441 | 1.055 |
| Visual / collision triangles | 74,520 / 25,248 | 99,616 / 33,706 |

Section measures use 41 matched transverse planes on the final visual mesh,
selecting the local closed contour enclosing the route origin. They exclude
separate obstacle holes and are resolution dependent. Visibility uses the existing
opaque collision-mesh diagnostic, not stereo reconstruction or policy performance.
The raw per-plane contours and all four single-module results are in
`exports/morphology_v01/morphology_measurements.json`. There is no aggregate
"realism score"; larger values are not necessarily better.

Single-run generation time was 8.38 s before and 23.19 s after, excluding rendering
and portable baking. The after case evaluates more field operators on a larger
grid. These timings were collected on one workstation with other work running;
they are not a repeated throughput benchmark. Per-module cases also remain in
`outputs/morphology_v01/{section_only,roughness_only,features_only,rockfall_only}`.

## Navigability and validation

The final `max(modified_void, protected_radius − route_distance)` remains after
all solid and void edits. Its radius is `robot radius + margin + 2.1 × collision
voxel`. Here it is 1.264 m, compared with the robot-plus-margin radius of 0.55 m.
This conservative generation allowance prevents truly tight robot-scale squeezes
in the current example. It is not silently removed to make screenshots dramatic.

Existing checks are unchanged: free-space and route connectivity, occupancy A*,
inside tests and spacing-corrected distances on both final meshes, sampled
shortcut screening, and slope limits. Invalid scenes remain failures. The two
paired cases additionally pass Blender BVH checks on closed and open meshes,
two-opening portal checks, and geometry/texture/crossing checks after GLB/OBJ
reimport. The earlier export attempt lacking the open-mesh audit is retained as
`outputs/morphology_v01/before_export_incomplete`; its successor has that audit.

There is no unconditional guarantee for arbitrary parameters, every possible
task, exact free-space topology, vehicle dynamics or perception/control error.
Protection can clip requested geometry; final mesh acceptance remains necessary.

110 tests passed, including backward-compatible zero-strength mesh equality,
protected-core sampling under all active modules, per-feature signed effects,
stable feature seeds, invalid control rejection, and deterministic named batch
sampling with unchanged underlying routes/materials.

## Reproduce and extend

From the repository root, generate to a new destination:

```powershell
.venv/Scripts/cave-compose.exe --config configs/morphology_v01/after.json --seed 97001 --output outputs/morphology_repro
.venv/Scripts/cave-dataset.exe --distribution configs/morphology_v01/distribution.json --num-scenes 2 --workers 1 --output outputs/morphology_batch_repro
```

The new named sampler `morphology_v01` starts from `topology_v03` and adds recorded
morphology parameters. Only this sampler permits `overrides.morphology` in batch
distributions. Existing samplers and their parameter supports remain unchanged.
Morphology priors currently have shared support across splits; this is not a new
morphology-OOD benchmark. The first batch smoke test uses a branching family;
its manifest retains initial failures and any same-seed retries. Both requested
scenes finished VALID: one on its first attempt, one after a same-seed retry of
an `OSError: access violation` during the metrics stage. Geometry validation had
already passed on the failed attempt. The native crash did not recur on retry;
its root cause is not established and production batch stability remains an
open engineering concern. This is not reported as two first-pass successes.

`scripts/measure_morphology.py` rebuilds the paired section diagnostics.
`scripts/render_morphology_comparison.py` runs inside Blender on the two exported
GLBs. `scripts/package_morphology_comparison.py` verifies the exports and rebuilds
the offline HTML gallery with download packages.

The next high-value step is a **scale-verified real-reference geometry audit**:
measure section shape, clearance gradients, multiscale surface spectra, curvature
and view-dependent occlusion on the development scans and generated caves with
matched sampling. Then fit parameter supports and compare held-out distributions,
controlling for voxel resolution, cave length and mean aperture. Follow this with
multi-seed navigability/acceptance reporting and frozen stereo-policy evaluation.
Adaptive protection along a checked route, connected keyhole/rift profiles and
physically anchored isolated boulders are useful follow-ups; they should be driven
by those measured gaps rather than another increase in unstructured noise.
