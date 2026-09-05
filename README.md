# Automated Cave Composer

Controllable procedural cave worlds for robot navigation research. Explicit turns,
branches, chambers and slopes become geological voids, independently validated
visual/collision meshes, navigation ground truth and geometric visibility metadata.

**V0:** six distinct checked examples plus a loop example, deterministic headless
generation, parallel dataset API, ID/OOD parameter distributions and Blender
previews. Stonefish export is an interface prototype; simulator runtime remains
unverified. No RL training or zero-shot generalization results are claimed.

## Start

Python 3.10+ (tested with 3.12.7), Blender for renders (tested with 5.2.1).

```bash
pip install -e ".[test]"
python generate.py --config configs/cave_b_sharp_turns.yaml --seed 42 --output outputs/my_cave
python generate.py --config configs/cave_e_chamber.yaml --seed 43 --output outputs/my_chamber --render --blender /path/to/blender --save-blend
python generate_dataset.py --distribution configs/train_distribution.yaml --num-scenes 100 --workers 4 --output outputs/train_100
```

On this workstation supply `--blender D:/Blender/blender.exe`. Elsewhere use PATH,
the `BLENDER_PATH` environment variable, or an explicit executable. No GUI is
needed: Python launches Blender with `--background`. Geometry generation itself
does not import Blender. Installed-package entry point: `cave-compose`.

```python
import cave_composer as composer
scene = composer.sample(split="train", difficulty="medium", seed=42,
                        output="outputs/api_sample")
scene = composer.generate("configs/cave_f_vertical.yaml", seed=17,
                          output="outputs/vertical_17")
```

No existing output is overwritten. Invalid scenes keep diagnostics and produce an
error / failed dataset record. They are never silently replaced with a new seed.
Eight exploratory batch scenes and ten unique final-distribution smoke scenes
were generated; this does not establish thousand-scene throughput.

## Inspect the delivered work

- [Full report](CAVE_COMPOSER_V0_REPORT.md)
- [Interactive local gallery](outputs/final/gallery.html)
- [Six-cave contact sheet](outputs/final/contact_sheet.jpg)
- [Independent architecture](docs/architecture_v0.md), [final decision](docs/architecture_final.md)
- [Specification and split contracts](docs/specification.md)
- [CAVERS material experiment](docs/cavers_material_experiment.md)
- [PLUME comparison](docs/plume_comparison.md)
- [Stonefish interface](docs/stonefish_interface.md)

Generated binaries live under ignored `outputs/`; run the configs to recreate
them after cloning. `docs/independent_checkpoint.json` and Git commit `7bf8111`
record the independent implementation before PLUME was accessed.

## Bundle

```text
visual/cave_visual.obj + .mtl + mesh.npz
collision/cave_collision.obj + mesh.npz
materials/rock_albedo.png + material.json
navigation/centerline.json + navigation_graph.json + junction_graph.json
navigation/spawn_points.json + goals.json + clearance.json + visibility_horizon.json
metadata/config.yaml + metrics.json + validation.json + provenance.json + checksums.json
previews/topology.png + overview.png + inside_01.png + inside_02.png
cave.blend                           # with --render --save-blend
stonefish/cave.scn + adapter.json     # optional adapter script
```

Source coordinates: metres, right-handed Z-up. Cave walls face into the void and
have sealed caps; the body is a free-space boundary for static concave collision,
not a convex solid enclosing the robot. Spawn/goal are inset. Nominal dimensions
are distinct from measured widths and certified spherical-robot clearance.

```bash
python scripts/export_stonefish.py outputs/my_cave --depth 20
blender --background --python scripts/audit_mesh_blender.py -- --scene outputs/my_cave
python scripts/validate_scene.py outputs/my_cave
python -m pytest -q
```

## Limits

Dense grids have a configurable allocation ceiling; limit workers by available
RAM. The field is not an exact SDF. Geological realism has visible route bias;
some safety-constrained necks become rounded. Grade changes and loop rejoin
connectors can be abrupt. No full recovered-topology isomorphism, exact-predicate
self-intersection proof, dynamic rock simulation, erosion physics, automatic LLM
parser, or measured PBR recovery is implemented. Blender shader bump is not
exported as a Stonefish normal map. Material statistics from a dataset prevent
calling that same dataset entirely untouched appearance OOD.

The source is prepared as an independent repository. No remote publication has
been performed. An owner-selected license is still needed before public release;
external CAVERS/Sketchfab assets are not bundled into the source repository.
