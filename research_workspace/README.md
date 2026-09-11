# CAVERN: generator, task handoff and paper

**Latest release:** [v02 handoff](COLLABORATOR_HANDOFF_v02.md),
[execution report](ROUND_V02_REPORT.md), and
[source-only reproduction](../reproducibility/README.md). Generated packs and
raw simulator outputs are local-only; the eight-cave/24-task generation pipeline
and the historical reports remain in Git. Paths under `outputs/` and `exports/`
below require local generation or the original archive. The
historical v01 notes below describe their original state; policy results and
the receiving Isaac Lab configuration remain pending.

The repository now has three connected areas: `cave_composer/` implements the
generator; this directory manages offline delivery and evidence; `overleaf/`
contains the paper. Existing APIs and dataset directories keep their names.
The only paper fact ledger is [CLAIM_EVIDENCE.yaml](../overleaf/CLAIM_EVIDENCE.yaml).

## Current evidence

- [Local audit](evidence/local_audit_v01.json) records the existing Git revision,
  dirty-state inventory, source hashes and raw artifact hashes. Three historical
  task packs contain 36 requests and 36 stored accepted tasks. Six later
  morphology configurations share one scene seed. This round rechecks file
  integrity and stored certificates; it does not rerun mesh-distance calculations.
- These are different generator snapshots. The repeated `0.3.0` package string
  alone is not an adequate experiment version. Keep source, configuration and
  exact delivered mesh hashes. Current handoff code does not retroactively
  change which generator produced old scenes.
- The collaborator's Isaac Lab platform is user-reported. No actual configuration,
  training manifest or runtime/policy log is locally available. Historical
  task-pack sensor interfaces remain intact.

## Draft delivery for the collaborator

`outputs/cavern_handoff_review_v01/` is a new, independent copy of the existing
branching, loop and multi-loop task packs. It contains `manifest.json`,
`manifest_digest.json`, `platform_profile.json`, `episodes.json` and verified
per-scene `assets/` directories. A file hash inventory locks textures and
metadata as well as meshes. It is for **interface review**, not a training
release or final test schedule. Its interior-pair episodes are not full-exit tasks.

```powershell
.venv/Scripts/python.exe scripts/prepare_navigation_handoff.py --check outputs/cavern_handoff_review_v01
.venv/Scripts/python.exe scripts/prepare_navigation_handoff.py --check outputs/cavern_handoff_review_v01 --require-runtime
```

The first checks offline integrity; the second intentionally fails because
runtime evidence is missing. This prevents accidental promotion of a validated
file bundle to an executed simulator scene. Read-only here means the utilities
refuse overwrite and detect modification; it is not an operating-system ACL
or a cryptographic signature against malicious rewriting.

To prepare a new review version, use a new directory and dataset ID:

```powershell
.venv/Scripts/python.exe scripts/prepare_navigation_handoff.py --packs outputs/pipeline_v04_tasks/branching_stereo outputs/pipeline_v04_tasks/loop outputs/pipeline_v04_tasks/multi_loop --output outputs/cavern_handoff_review_v02 --dataset-id cavern_interface_review_v02
```

Never change the collaborator's active manifest in place. Its location is
currently unknown. Review copies do not update the running training version.

## Observation, action and simulation contract

[platform_proposal_v01.json](contracts/platform_proposal_v01.json) is the
user-authorized proposal, with every actual-platform field **UNCONFIRMED**.
Stereo RGB, relative goal, IMU, pressure and previous action are candidate
observations. Relative goals computed from simulator truth establish a
**localization-assisted** condition. The provisional action is normalized body
twist with six components; rates, physical limits and the vehicle controller
remain unresolved. This proposal does not change the historical stereo-only
pack specification or assert what the current actor consumes.

World/body/camera axes, quaternion order, metric units, per-instance transforms,
robot envelope, resets, goals and budgets must be checked against the real
platform. Maps, construction routes and search witnesses are privileged;
critic-only access needs an explicit configuration. Actor inputs must be
declared by key, dtype, shape, frame, latency, normalization and source.

Before a training release, the collaborator must return: simulator and adapter
versions; imported asset hashes; collider cooking/scale and normal checks;
transform round-trips for meshes, resets and cameras; paired camera renders;
collision probes; distinct physical cave identities across parallel instances;
reset/goal and exit-crossing checks; actual observation/action schemas and
control rates. Log that one parameter set is shared across all caves within
each algorithm/config/seed. FlashSAC and recurrent visual PPO are separate runs.

## Results returned from the training platform

See [results.schema.json](contracts/results.schema.json),
[run_template.json](contracts/run_template.json), and
[result_protocol.md](contracts/result_protocol.md). The empty JSONL file is a
format starting point, not an experimental run. No synthetic outcome rows are
provided. Each fixed episode must have one record, including explicit `not_run`.
The importer validates IDs, hashes, finite metrics, terminal categories and
trajectory bytes, then writes a fresh intake directory. It neither trains nor
automatically claims a policy result is verified.

## Source isolation and next work

[source_registry_v02.yaml](source_registry_v02.yaml) conservatively groups
existing metadata, without reading final OOD pixels/geometry for tuning.
Run `python scripts/audit_cavern_sources.py` to check declared consistency.
No source is currently approved as untouched final OOD. Four historical
Sketchfab model files belong to two cave groups; the intended fifth model is
unconfirmed. Previously used texture sources remain prior/development sources.

The newly cropped real reconstructions are uncalibrated. Their endpoints and
positive distance to observed triangles do not establish complete interior
coverage, metric robot clearance or successful execution. Training long and
testing short portions of the same cave is within-source spatial holdout.

Prioritized experiments and missing author/collaborator decisions are in
[PAPER_PLAN.md](../overleaf/PAPER_PLAN.md). No RL job, remote upload or Git push
is part of this round.
