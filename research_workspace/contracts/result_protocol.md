# Collaborator result intake, version 1

One `run.json` identifies an algorithm/configuration/training seed and frozen
checkpoint; one fixed `episodes.json` contains the predeclared episode list;
`results.jsonl` contains exactly one record per episode. Separate algorithms,
training seeds or checkpoint choices require separate run directories.

1. Agree the episode list and archive its file SHA256 **before policy outcomes**.
   Include `episode_id`, `scene_id`, source group, split, task kind, reset, goal,
   metric scale, robot envelope and task budget. Review-list episodes are not
   automatically approved evaluation episodes. Do not remove failed episodes.
2. Fill every null field in `run_template.json` from the actual run and set
   `template_only` to false only when the receipt is complete. Record
   configuration, dataset manifest, normalizer, preprocessing and checkpoint
   SHA256; provide those artifacts or an independently accessible provenance
   receipt for later review. Record the fixed-episode SHA256 and a preselection
   declaration. The declaration alone cannot prove chronology.
3. Save raw trajectories with timestamps, positions/orientations in stated
   coordinates, actions, terminal events and simulator time. Record each file's
   SHA256 and portable relative path. Store logs before aggregation. A valid
   file hash does not validate dynamics or distinguish a simulated trajectory
   from one fabricated elsewhere; independent runtime review remains required.
4. `outcome` and the four boolean terminal flags describe the mutually exclusive
   terminal category after the declared precedence. They are **not cumulative
   contact counters**. If contacts occur earlier, retain those in raw logs.
   Never encode infrastructure aborts as ordinary timeout: report `not_run`
   with an explicit abort/nonexecution reason, null episode elapsed time, and
   retain the partial raw log separately for audit. Report aborts separately
   in all denominators, including a scheduled-episode denominator.
5. Elapsed time is nonnegative simulation episode time in seconds. Remaining
   traversable distance is in calibrated metres from a versioned estimator;
   do not substitute Euclidean goal distance silently. Unavailable distance
   must be null with a reason and estimator-status description. For `not_run`,
   both metric missing reasons and `not_run_reason` are required.

```powershell
.venv/Scripts/python.exe scripts/import_navigation_results.py --run PATH/run.json --episodes PATH/episodes.json --results PATH/results.jsonl --root PATH --output outputs/collaborator_intake_NEW
```

Import validates the episode-file hash and exact episode membership, per-record
checkpoint/data identity, finite nonnegative metrics, terminal consistency,
and trajectory bytes. It refuses overwrite. It copies original receipts and
trajectories without calculating performance claims. Revalidate the received
trajectory paths relative to `outputs/collaborator_intake_NEW/trajectories`.

Checkpoint/configuration/normalizer/dataset hash **format** is checked by this
offline intake; their actual bytes and relationship to runtime require the
external artifacts. The status remains `adapter_checked`, not
`simulator_runtime_verified` or `policy_evaluated`. A reviewer promotes evidence
only after verifying those artifacts, actual execution, fixed preprocessing,
frozen weights and no within-episode interventions. Human-approved results must
still be checked against the claim ledger before entering paper tables.

Aggregation must report per-source/scene and per-training-seed outcomes,
scheduled/executed/aborted denominators, and uncertainty at the independent
scene/source and training-run levels. Do not treat many tasks in one cave as
many independent caves. Compare restricted/full data inside the same learner
with matched budgets before comparing differently structured algorithms.
