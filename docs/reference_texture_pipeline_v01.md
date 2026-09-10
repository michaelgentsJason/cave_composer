# Reference rock textures in Cave Composer

The generator now accepts a pinned local texture library. The first example is
[the easy gallery](../exports/easy_reference_texture_v01/index.html), with three
views rendered from its exported GLB, the full route, GLB, an OBJ ZIP containing
its MTL and textures, and a packed Blender inspection scene.

## What is connected

`Local scan atlas → UV-interior candidate crops → visual crop review → periodic
boundary processing → pinned texture library → appearance-seed selection →
scene-local material → Blender projection → portable UV-baked GLB / OBJ`.

Four reviewed patches come from three scans and two conservatively grouped cave
sources. Their atlas coordinates, image hashes, native dimensions, attribution,
and transformations are recorded in
[library.json](../materials/reference_rock_v01/library.json). This implementation
transfers captured rock appearance; it does not import scanned cave geometry.
Candidate extraction targets the supplied GLBs and requires the optional
`reference-import` dependencies. It is not a universal material extractor.

`material.texture_id` fixes a patch for a controlled example. Omitting it samples
uniformly over sorted library entries using `material.seed`, then selects a
quarter-turn rotation. The same seed and pinned library reproduce the selection.
`texture_period_metres` controls projection scale (1.2 m here, artist chosen).
The texture is fixed in scene coordinates, so camera motion or switching stereo
eyes does not resample it. Existing procedural materials remain the default.

## Generate and batch

Run from the repository root after installation (`pip install -e .`). Use fresh
output directories; scene generation intentionally refuses to overwrite one.

```powershell
.venv/Scripts/cave-compose.exe --config configs/easy_reference_texture_v01.json --seed 97001 --output outputs/reference_texture_repro --render --blender D:/Blender/blender.exe
.venv/Scripts/cave-dataset.exe --distribution configs/reference_texture_distribution_v01.json --num-scenes 10 --output outputs/reference_texture_batch --render --blender D:/Blender/blender.exe
```

The example config fixes the Sump 9 gray-blue patch. The batch distribution
leaves the texture ID and material seed unset in its overrides, preserving each
sampled scene's appearance seed. This batch command is a usage example; the
delivered demo contains one newly generated easy cave.

Generation validates the library manifest SHA-256, each selected library's tile
hashes, reviewed-entry status, and local paths before building geometry. The
material and credits are copied into each bundle. The portable textured exporter
also carries `ATTRIBUTION.txt` and `material_provenance.json`. Changes to the
library require deliberate repinning. Git attributes preserve pinned bytes.

## Delivered example and checks

- Geometry seed 97001; appearance seed 97011; 50.38 m main route, two 30-degree
  bends, nominal 6 m width / 4.8 m height, no branches.
- Independent occupancy search and both closed-reference mesh checks pass.
- The separate portal derivative has two actual openings. Reimported GLB and
  OBJ both pass texture, geometry, boundary, and crossing-path checks. The
  visual crossing-path radius lower bound is 1.425 m; required radius is 0.55 m.
- Both meshes were rebuilt with a procedural material at the same geometry
  seed; exact vertex/face hashes match. See the gallery's
  `geometry_appearance_check.json` for the scoped invariance check.
- 92 tests passed, including 9 reference-material tests covering reproducibility,
  selection, attribution, invalid configs, changed hashes, and path containment.
- Rerender inspection views with `scripts/render_textured_asset_views.py` inside
  Blender. Rebuild the offline gallery and OBJ ZIP with
  `.venv/Scripts/python.exe scripts/package_reference_texture_demo.py`.

## Scope for training

The source atlases are 4096 square; approved native crops are only 132–224 square.
The exported 4096-square UV maps do not add captured detail. Periodic processing
reduces boundary discontinuities, but repeated features and residual capture
illumination can remain. This is not intrinsic albedo recovery. Normal detail
is procedural, roughness is configured, and neither is measured from the scans.

The sources used here are registered as development/prior data. Their source
groups must not be presented as untouched zero-shot test caves. Four patches
are an initial appearance library, not evidence of large material diversity or
improved policy generalization. Those claims require training and held-out
evaluation. The existing 30-scene export collection was not regenerated.
