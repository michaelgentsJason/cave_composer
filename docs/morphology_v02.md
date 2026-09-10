# Wider morphology examples

The current inspection presets use **7.5 m nominal width and 6.0 m nominal
height**, both 25% larger than the 6.0 m × 4.8 m v01 examples. Local feature
`span` and `depth` are also scaled by 1.25. Route length, turns, feature positions
along the route, longitudinal feature lengths, robot size, voxel sizes, texture
and seeds remain fixed. These are nominal dimensions: irregular walls and
obstacles change the measured local free aperture.

Open the [new comparison gallery](../exports/morphology_v02/index.html). It contains
three matched views in textured and clay modes, whole-route geometry, measured
sections and downloads of both textured GLBs, OBJ packages and Blender scenes.
The [v01 gallery](../exports/morphology_v01/index.html) remains available.

| Optimized scene | v01 | Wider v02 |
|---|---:|---:|
| Nominal width / height, m | 6.0 / 4.8 | 7.5 / 6.0 |
| Independent path collision-mesh clearance lower bound, m | 1.055 | 1.302 |
| Mean continuously visible route, m | 17.496 | 19.228 |
| Main-route length, m | 50.378 | 50.378 |

The widening is applied consistently to the before, after and four single-factor
configurations under `configs/morphology_v02`. All six generated bundles passed
the unchanged navigation validation checks. The before/after export build also
performs closed/open BVH audits, portal checks and portable GLB/OBJ reimport checks;
the saved reports in the gallery are the authoritative results.

The generator-wide defaults, existing dataset split rules and the earlier
30-scene collection are unchanged. Select the wider presets explicitly, or use
them as the base for subsequent scene configurations. This release also includes
the preceding reference-texture library and opt-in structural morphology work;
see [the geometry audit](morphology_v01.md) and
[reference materials](reference_texture_pipeline_v01.md).

## Reproduction

From the repository root, with dependencies installed and Blender available:

```powershell
.venv/Scripts/python.exe scripts/build_morphology_comparison.py --blender D:/Blender/blender.exe
```

The builder defaults to v02, records geometry seed 97001, creates the six bundles,
measures the paired sections, audits and exports both full cases, renders matched
views, verifies portable exports and packages the HTML gallery. Existing complete
bundles are checked before reuse; mismatched configurations or incomplete exports
are rejected. `--configs`, `--source`, `--exports` and `--seed` support separate runs.

Delivered model files are in `exports/morphology_v02/{before,after}`; intermediate
generation bundles and logs are in `outputs/morphology_v02`. Source scan downloads
stay local in `sketchfab_caves`; the repository includes the reviewed derived
texture patches with attribution, source links and processing records.

The full suite passed **110 tests** before publication. The geometric check is
for accepted paths and the configured spherical envelope. It is not a dynamics
guarantee or evidence of real-world policy generalization.
