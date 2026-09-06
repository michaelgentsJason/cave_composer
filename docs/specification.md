# CaveSpec v1

All geometry uses metres, signed angles use degrees, +Z is up, +X is the initial
heading and positive turns rotate left in XY. A straight's length is 3D arc length;
a circular turn's radius is horizontal and its slope creates a helical grade.
Main route command lengths include cap-center to cap-center. Spawn/goal are inset.

```yaml
schema_version: 1
name: example
corridor: {width: 4, height: 3.6, variation: 0.17, section: irregular}
robot: {radius: 0.35, margin: 0.20}
mesh: {visual_voxel: 0.20, collision_voxel: 0.34, max_voxels: 18000000}
route:
  - {straight: 15}
  - {turn: 60, radius: 4}
  - {straight: 10}
  - {turn: -90, radius: 4}
  - {straight: 12, slope: -12, width: 3.2, section: fracture}
  - {turn: 120, radius: 4.5}
  - {straight: 20}
branches:
  - at: 0.25
    heading: -90
    route: [{straight: 12}]
chambers:
  - {at: 0.6, radii: [7, 6, 4], lobes: 5, style: irregular}
bottlenecks:
  - {at: 0.8, length: 5, width: 2.8, height: 2.8}
geology: {amplitude: 0.35, strata: 0.17, formations: 15}
material: {style: limestone, seed: 100, roughness: 0.87}
```

The `at` value for branches/chambers selects a normalized main-route sample index;
because route sampling is nearly uniform it approximates normalized arc length.
Bottleneck `at` uses normalized arc length exactly. Rejoin branches specify
`rejoin_at` and receive a linear connector to that sampled main-route location;
this connector may introduce a sharp corner and is separately validated.
Use `cave_g_loop.yaml` for an explicit example.

Section choices: oval, elliptical, flattened, tall, triangular, asymmetric,
fracture, irregular. Width/height remain independent parameters: choosing `tall`
does not secretly double the height. Width/height overrides blend continuously
over the command. Section-shape exponent changes currently occur at command
boundaries and are blended only through the volume union / sampling; precise
continuous interpolation of all shape parameters is a future improvement.

The safety envelope radius is `robot.radius + margin + 2.1*collision_voxel`.
The last term is a conservative construction allowance for voxel evaluation.
Specs with requested dimensions below twice that radius plus 0.1 m are rejected;
use a finer collision grid for smaller physical squeezes. Nominal corridor width
is not a claim of exact wall-to-wall width after geological operations. Metrics
record measured transverse widths and mesh-clearance lower bounds.

There is no scalar `length` that competes with the route grammar: sum command
lengths (including arc lengths) to request a total. Counts of branches and chambers
are list lengths. S-turn/double-turn/multi-turn/hairpin are command compositions.
Floor clutter is wall-attached field subtraction; dynamic loose rocks are absent.

Material geometry seeds are independent. `material.palette` optionally accepts
three RGB triplets in [0,1]. `language.from_prompt(prompt, adapter)` is an explicit
protocol for a future parser/LLM and validates its output. No built-in general
natural-language understanding is claimed.

## Split contract

`train`, `validation`, `id_test`: same supports, disjoint seed namespaces. Factors
are sharp (60–90°), narrow (3.0–3.6 m) and descent (-18 to -10°). The conjunction
of all three is excluded. Other values: turn 20–55°, width 4.3–6 m, slope -4 to 4°.
`ood_composition` holds out that conjunction, while each individual factor was
available in training. `ood_geometry` uses 120–165° primary bends, 2.7–2.95 m
width and -28 to -22° descent. Second bends scale the primary angle by -0.8.
These are **nominal parameter supports**, not guarantees that measured widths
have disjoint distributions. Realistic OOD scans remain external.

Dataset distribution accepts split, difficulty, base_seed and mesh/material
overrides. No rejected seed is silently substituted. Parallel workers write to
separate directories. Manifest schema 2 supports incremental progress, verified
scene-level resume and explicit same-seed retries, including archived failure
artifacts. Its config/code/dependency/render contract remains fixed across a
resumed run. See [pipeline usage](pipeline.md). Smoke tests do not establish
1,000-environment throughput.
