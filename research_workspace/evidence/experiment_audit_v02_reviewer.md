Overall verdict: **WARN**. I found **no CRITICAL integrity failure**: no fake ground truth, no self-normalized score inflation, and no phantom successful PLUME baseline. The main risk is interpretive: the corrected C1 acceptance numbers rely on a post-preregistration delivery checker, and several outputs are small-scope simulation/proxy evaluations that must be labeled exactly that way.

**MAJOR / Actionable Findings**

1. **Canonical acceptance uses a post-preregistration checker.**  
   The preregistered source hash for `cave_composer/delivery_validation.py` is `1d011...` in `outputs/c1_pilot_v02/preregistration.json:250`, while the recheck uses checker hash `214695...` in `outputs/c1_pilot_v02/delivery_recheck.json:3`. The change is declared as an importer correction in `outputs/c1_pilot_v02/delivery_recheck.json:2`, and the code performs exact-position vertex welding in `cave_composer/delivery_validation.py:30-35`.  
   Concrete correction: any paper/table using the 15/18 accepted number must say it is **after the declared exact-position OBJ seam recheck**, not the original per-run `accepted` field. Do not call this an unmodified preregistered checker result.

2. **Raw per-run `accepted` fields conflict with corrected summary acceptance.**  
   Example: `outputs/c1_pilot_v02/results/00.json:529-540` shows original delivered check `FAIL` because the visual mesh failed `closed_reference_protocol_not_applicable`, and `outputs/c1_pilot_v02/results/00.json:26494` says `accepted: false`. The corrected recheck for the same file says `PASS` and `accepted: true` in `outputs/c1_pilot_v02/delivery_recheck.json:6-57`. The analysis script intentionally overwrites acceptance from recheck at `scripts/analyze_c1_pilot_v02.py:20-23`, and documents this at `outputs/c1_pilot_v02/summary.json:6`.  
   Concrete correction: use `summary.json` / `delivery_recheck.json` as the canonical acceptance source, and never aggregate `results/*.json.accepted` directly.

3. **Protection figure includes a failed diagnostic scene.**  
   `scripts/analyze_c1_pilot_v02.py:78-93` selects `request_04` full vs no-protection and plots the no-protection mesh even when A* fails. The underlying no-protection stress row is rejected with `endpoint_not_in_conservative_robot_space` in `outputs/c1_pilot_v02/results/13.json:96-113` and summarized as failed in `outputs/c1_pilot_v02/summary.json:379-391`.  
   Concrete correction: caption this as a **retained failed diagnostic no-protection scene**, not an accepted output or navigation benchmark success/failure rate.

4. **External PLUME baseline has no successful result.**  
   All recorded attempts have `exit_code: 1` in `outputs/c1_pilot_v02/external/plume/attempts.json:2-40`; the postprocessed attempt also has `exit_code: 1` with an adapter reason in `outputs/c1_pilot_v02/external/plume/external_graph_postprocessed_attempt.json:1-15`. `summary.json` keeps `external_plume_paired_result` as `null` at `outputs/c1_pilot_v02/summary.json:413`.  
   Concrete correction: do not report a paired PLUME comparison; only report an unsuccessful smoke/applicability attempt.

**Checklist**

- **A. Ground Truth Provenance: WARN**  
  Main C1 is `simulation_only` / `self_supervised_proxy`: it checks generated meshes against requested configs, generated centerline endpoints, and final mesh certificates. This is labeled as proxy scope in `outputs/c1_pilot_v02/preregistration.json:215-216` and `outputs/c1_pilot_v02/summary.json:2-7`. Analytic fault fixtures have fixed source labels in `scripts/audit_c1_faults_v02.py:13-19` and results provenance in `outputs/c1_pilot_v02/faults/results.json:2-3`.

- **B. Score Normalization: PASS**  
  I found no metric divided by the model’s own max/min/mean to inflate scores. Yield is `final_passes / requested` in `scripts/analyze_c1_pilot_v02.py:64-65`; timing is total seconds divided by accepted count in `scripts/analyze_c1_pilot_v02.py:41-44`; geometry uses nominal dimensions or shape ratios in `scripts/run_c1_pilot_v02.py:104-119`.

- **C. Result Existence / Numeric Consistency: WARN**  
  Required JSONs and PNGs exist. Summary group counts match the delivery recheck: normal full/no-protection/restricted are 4/4; stress full is 1/2; stress no-protection is 0/2; stress restricted is 2/2 at `outputs/c1_pilot_v02/summary.json:316-410`. Figure provenance hashes all 18 result files plus summary/recheck inputs in `overleaf/figures/generated/c1_v02/provenance.json:4-25`. The warning is the raw-result-vs-recheck acceptance conflict above.

- **D. Dead Code Detection: PASS for listed C1 eval scripts**  
  `measurements()` is called by the worker at `scripts/run_c1_pilot_v02.py:156`; `verify_delivered_task()` is called in the run, recheck, and fault audit at `scripts/run_c1_pilot_v02.py:152`, `scripts/recheck_c1_delivery_v02.py:14`, and `scripts/audit_c1_faults_v02.py:28`; plotting `save()` is called at `scripts/analyze_c1_pilot_v02.py:77` and `scripts/analyze_c1_pilot_v02.py:101`. Portal helpers are not exercised by the listed C1 outputs.

- **E. Scope Assessment: WARN**  
  Scope is small: 6 paired base requests, 18 single attempts, no retries, 4 normal and 2 stress base requests, declared in `outputs/c1_pilot_v02/preregistration.json:5-6` and `outputs/c1_pilot_v02/preregistration.json:207-213`. The summary correctly says descriptive pilot with no significance/generalization claim at `outputs/c1_pilot_v02/summary.json:2`. Keep paper language to “pilot”, “six paired base requests”, and “descriptive”.

- **F. Evaluation Type: WARN / classified**  
  Main pilot: `simulation_only` + `self_supervised_proxy`.  
  Delivery recheck: geometric closed-reference certificate, with exact-position OBJ seam import adapter.  
  Fault fixtures: analytic simulation controls.  
  External PLUME: unsuccessful smoke/applicability attempt, no comparable result.

Recommended claim posture: the C1 artifacts support a **descriptive pilot claim under corrected exact-position OBJ seam recheck**, with 15/18 final accepted attempts and clear stress failures. They do not support broad robustness, real-world navigation performance, statistical generalization, or PLUME superiority claims.
