# Reproduce Cave Composer from source

The Git repository contains code, configurations, the small attributed texture
library, paper sources, showcase figures and historical validation receipts.
Generated scene collections, raw experimental output bundles, packed Blender
scenes and compiled paper archives are **local-only**. Both `outputs/` and
`exports/` are ignored. Their previous versions were removed from published Git
history, so a normal clone no longer downloads those assets.

The generator and navigation algorithms are unchanged by this packaging update.
Generate new assets on the receiving machine using the commands below. Original
local assets and failed runs were retained on the producing machine.

The [source-only acceptance record](verification_v04.json) covers 136 passing
tests, fresh generation/task/portal checks, a newly baked textured GLB/OBJ and
paper compilation from a checkout without old scene collections.

## Clean installation and verification

Use CPython 3.12 (locally tested with 3.12.7):

```powershell
git clone https://github.com/michaelgentsJason/cave_composer.git
cd cave_composer
python -m venv .venv
.venv/Scripts/python.exe -m pip install --only-binary=:all: -r requirements-lock.txt
.venv/Scripts/python.exe -m pip install --no-deps --no-build-isolation -e .
.venv/Scripts/python.exe -m pip check
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe scripts/check_reproducibility.py --output outputs/reproduce_NEW
```

On Unix use `.venv/bin/python`. Do not enable system-site-packages. Activate
this environment before using the shorter `python` commands below.

The default check generates the wider irregular cave twice, verifies both
bundles, compares exact mesh arrays and material bytes, samples three tasks,
and cuts and checks entrance/exit portals. It requires **no archived assets**.
Use a new output directory each time; logs and failures are retained there.

To also bake and reimport a newly generated textured GLB/OBJ, and compile the paper:

```powershell
python scripts/check_reproducibility.py --output outputs/reproduce_FULL_NEW --blender D:/Blender/blender.exe --paper
```

Replace the Blender path (locally tested with 5.2.1). The paper requires
pdfLaTeX/BibTeX. Core generation and navigation checks require neither Blender
nor Isaac Sim. CI runs the default source-only check; optional steps are
explicitly recorded as `NOT_RUN` when not requested.

## Generate a textured cave

```powershell
python generate.py --config configs/morphology_v02/after.json --seed 97001 --output outputs/my_cave
python scripts/build_navigation_tasks.py --scene outputs/my_cave --output outputs/my_tasks --count 3 --seed 88200
python scripts/export_portals.py --scene outputs/my_cave --output outputs/my_open_cave
blender --background --python-exit-code 1 --python cave_composer/blender_audit.py -- --scene outputs/my_open_cave
blender --background --python-exit-code 1 --python scripts/export_textured_cave.py -- --scene outputs/my_open_cave --output exports/my_cave --name cave
```

Use your Blender executable in place of `blender` if it is not on PATH. GLB
embeds its textures; keep OBJ together with MTL and the texture directory.
Closed-reference task verification precedes portal cutting; the open export
has its own checks. Imported geometry requires the receiving simulator's checks.

Configs and seeds for the previous **15 easy / 10 medium / 5 hard** collection
are preserved in [asset_recipes_v01](../configs/asset_recipes_v01/manifest.json).
For example, regenerate the hard showcase's source request:

```powershell
python generate.py --config configs/asset_recipes_v01/hard_005.json --seed 1080501 --output outputs/hard_005_NEW
```

Each recipe records its seed and original terminal inset. Use the same generation
and export steps for other recipes. These replay requested configurations with
the current code; they are not a claim of identical historical outcomes.
To sample a new batch with automatic task checks and a gallery:

```powershell
python generate_dataset.py --distribution configs/topology_distribution.yaml --num-scenes 30 --workers 2 --output outputs/caves_NEW
```

This batch samples its configured distribution; it is not the fixed 15/10/5
recipe collection. Generated galleries can be opened locally after generation.

## Generate the pilot and training interface pack

No downloaded pilot meshes are needed. First initialize and execute the six
base requests with three arms, keeping every attempted outcome:

```powershell
python scripts/run_c1_pilot_v02.py --root outputs/pilot_NEW --initialize
python scripts/run_c1_pilot_v02.py --root outputs/pilot_NEW
python scripts/recheck_c1_delivery_v02.py --root outputs/pilot_NEW
python scripts/analyze_c1_pilot_v02.py --root outputs/pilot_NEW --output outputs/analysis_NEW
```

Next build the eight normal full/restricted cave requests and their fixed task
requests, using new destinations:

```powershell
python scripts/prepare_c2_pilot_v02.py --pilot outputs/pilot_NEW --output outputs/pretraining_NEW
python scripts/export_c2_portable_v02.py --root outputs/pretraining_NEW --blender D:/Blender/blender.exe
python scripts/export_c2_portable_v02.py --root outputs/pretraining_NEW --blender D:/Blender/blender.exe --inset 0.05
python scripts/freeze_c2_release_v02.py --source outputs/pretraining_NEW --pilot outputs/pilot_NEW --output exports/pretraining_NEW
python scripts/check_c2_release_v02.py --release exports/pretraining_NEW
```

The first export retains initial terminal-plane outcomes; the second uses the
declared inset. Do not substitute rejected requests with new seeds. The previous
local run produced eight caves and 24 tasks; each new run must pass its own
checks. This is a geometric task interface, not an RL training result. Actual
actor, vehicle, action and runtime settings belong to the receiving platform.

## Paper and historical records

```powershell
python scripts/build_cavern_paper.py
python scripts/package_cavern_overleaf.py --output outputs/paper_NEW.zip
```

The PDF is written to `overleaf/build/main.pdf`. The ZIP includes the paper's
figures. The build uses committed figures unchanged; `--render-schematics`
explicitly redraws only the two overview diagrams. The manuscript remains a
working draft with visible result placeholders.

[verification_v03.json](verification_v03.json) and `acceptance_v03/` are
**historical receipts from the earlier asset-inclusive checkout**. Their bytes
and original claims were retained; they do not mean those raw assets are still
in this source checkout. The paper's evidence ledger and reports also refer to
local historical files and pre-cleanup commit IDs. Do not replace those records
with newly generated results and present them as the original experiments.

On a machine that retains the original full local archives, explicit archive
checks remain available:

```powershell
python scripts/check_reproducibility.py --output outputs/archive_check_NEW --archives --all-assets
```

This intentionally fails if the requested archives are absent. The default
source check does not silently label historical evidence as verified.

## External inputs and reproducibility scope

The attributed reference patches in `materials/reference_rock_v01` are small
runtime inputs and remain included. Original Sketchfab downloads and Metashape
reconstructions remain external; they are unnecessary for the workflows above.
Their metric scale and final-test eligibility require separate confirmation.

Exact same-seed mesh and texture comparisons are made within the pinned
environment. Cross-platform floating-point equality, identical rendering across
GPU drivers, historical timings, policy success and real-world transfer are
not established by these checks. No RL checkpoints or simulator installations
are included.

After the history cleanup, use a **new clone** on other devices. Preserve any
uncommitted work in an old clone before switching; do not merge or push its old
asset-containing history back into the cleaned branch.
