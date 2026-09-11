# Reproduce the Cave Composer release

This checkout contains the generator, attributed reference-texture patches,
30 textured difficulty assets, the eight-cave/24-task interface release,
recorded pilot inputs and failures, and the current manuscript and figures.
The release targets a **fresh CPython 3.12 environment**. Local acceptance uses
Python 3.12.7 and Blender 5.2.1; CI exercises Python 3.12 on Windows. Other
operating systems are not yet covered by the release acceptance run.

The [recorded clean-clone acceptance](verification_v03.json) passed 136 tests,
all 30 delivered assets, repeated same-seed geometry, a fresh textured export,
the complete eight-cave/24-task rebuild, and a standalone Overleaf compilation.
The initial install/checkout defects and their repairs are recorded there.
Download the [self-contained Overleaf ZIP](../overleaf/cave_composer_overleaf.zip)
or the [compiled PDF](../overleaf/main.pdf).

## Clean installation and verification

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

On Unix, use `.venv/bin/python`. Do not enable system-site-packages. The lock
includes runtime, transitive, test and build dependencies. Extracting new
patches from external scans additionally requires the `reference-import` extra;
generating with the bundled patches does not.

The check verifies archived claim files and the frozen eight-scene package,
generates the wider irregular case twice, compares exact mesh arrays and
material bytes, samples three tasks, opens and checks portals, and recomputes
the pilot table from raw records. Each invocation requires a new output folder.
Logs, failures and `verification.json` remain there; archived evidence is read-only.

For the complete local check, including all 30 assets, a NEW textured GLB/OBJ
bake/reimport and the paper build:

```powershell
.venv/Scripts/python.exe scripts/check_reproducibility.py --output outputs/reproduce_FULL_NEW --all-assets --blender D:/Blender/blender.exe --paper
```

Replace the Blender path. Paper compilation requires pdfLaTeX and BibTeX;
Poppler is useful for inspecting the PDF. Generation, planning and checking
included assets need neither Blender nor Isaac Sim. CI runs the core check;
its report explicitly marks optional steps not run.

## Included assets and manuscript

- `exports/caves_difficulty_v01/index.html`: 15 easy, 10 medium, 5 hard scenes.
- `exports/morphology_v02/index.html`: paired wider geometry examples.
- `exports/cavern_pretraining_v02/README.md`: eight caves, 24 tasks and splits.
- `overleaf/main.pdf`: compiled snapshot; `overleaf/main.tex` is the source.

GLB embeds images; copy OBJ with MTL and its textures. Apply the recorded
Z-up/Y-up transform once and use static nonconvex triangle collision, not a
solid convex hull. Open HTML after cloning, or serve the repository using
`python -m http.server 8765 --bind 127.0.0.1`.

`python scripts/build_cavern_paper.py` compiles the included figures unchanged.
Its optional `--render-schematics` regenerates only the two overview diagrams.
`python scripts/package_cavern_overleaf.py --output outputs/paper_NEW.zip`
creates a self-contained Overleaf archive. The nine-page manuscript remains a
working draft with visible result placeholders, not a submission-ready paper.

## Reanalyse or rerun the recorded pilot

`outputs/c1_pilot_v02/` contains all 18 configurations and raw outcomes,
failed cases, measured contours, meshes, original importer checks, declared
seam rechecks and the original source snapshot. Selected historical evidence
under `outputs/` is deliberately tracked; new outputs remain ignored.

Run the following with the virtual environment activated:

```powershell
python scripts/analyze_c1_pilot_v02.py --root outputs/c1_pilot_v02 --output outputs/analysis_NEW
python scripts/recheck_c1_delivery_v02.py --root outputs/c1_pilot_v02 --output outputs/recheck_NEW.json
python scripts/run_c1_pilot_v02.py --root outputs/pilot_NEW --initialize
python scripts/run_c1_pilot_v02.py --root outputs/pilot_NEW
python scripts/recheck_c1_delivery_v02.py --root outputs/pilot_NEW
python scripts/analyze_c1_pilot_v02.py --root outputs/pilot_NEW --output outputs/analysis_rerun_NEW
```

Reanalysis uses measured historical times; rerunning records new times. Timing,
timestamps, paths and PDF metadata are not expected to be byte-identical. Exact
repeat mesh equality is checked within the pinned environment; cross-platform
floating-point equality and identical images across drivers are not claimed.
The original pilot predates later importer fixes. Its original rejections and
source snapshot remain intact; a current-code rerun is a separate experiment.

## Rebuild a separate training interface release

Use the published normal pilot meshes as inputs and fresh destinations:

```powershell
python scripts/prepare_c2_pilot_v02.py --pilot outputs/c1_pilot_v02 --output outputs/pretraining_NEW
python scripts/export_c2_portable_v02.py --root outputs/pretraining_NEW --blender D:/Blender/blender.exe
python scripts/export_c2_portable_v02.py --root outputs/pretraining_NEW --blender D:/Blender/blender.exe --inset 0.05
python scripts/freeze_c2_release_v02.py --source outputs/pretraining_NEW --pilot outputs/c1_pilot_v02 --output exports/pretraining_NEW
python scripts/check_c2_release_v02.py --release exports/pretraining_NEW
```

The first export retains the initial terminal-plane attempt, including any
boundary warning; the second uses the declared inset and supplies the release.
These commands preserve `exports/cavern_pretraining_v02`. The result is an
offline geometric interface pilot; actual actor, vehicle, action and training
settings need the receiving platform's values. See
`research_workspace/COLLABORATOR_HANDOFF_v02.md` for the optional Isaac Sim test.
Recorded two-scene Isaac frames are historical evidence, not policy results.

## External inputs and evidence scope

Raw Sketchfab downloads and `exports/metashape_crops_v01` remain external local
inputs. Metashape metric scale and final-test eligibility are unresolved.
Processing scripts and source-role records are included; obtaining/configuring
these inputs is a separate step. The private `real_source_preparation` figure
is excluded. None is needed by the checks above or the main manuscript build.

The release contains no RL checkpoints, final real-source transfer results or
calibrated underwater optics model. PLUME dependency/API failure logs and its
upstream revision are retained; its vendored source and environment are excluded.
Historical reports retain their dates and may reference additional local runs;
the current release instructions and acceptance receipt define what was checked.
