# Experiment audit v02

Date: 2026-09-10. Auditor: independent GPT-5.5 xhigh, Codex backend.
Overall verdict and integrity status: **WARN**. The complete reviewer response
is [experiment_audit_v02_reviewer.md](experiment_audit_v02_reviewer.md).
This is a scoped C1 audit, not an assurance of all C2/C3 runtime claims.

| Checklist | Reviewer status |
|---|---|
| A. Ground truth provenance | WARN: simulation and mesh-derived geometric proxies |
| B. Score normalization | PASS |
| C. Result existence / consistency | WARN: original importer rejects vs declared seam recheck |
| D. Called evaluation code | PASS for listed C1 scripts |
| E. Scope | WARN: six fixed base requests, descriptive pilot |
| F. Evaluation type | Simulation-only, geometric proxies; analytic controls |

Executor responses to actionable findings, without changing the reviewer verdict:

1. Evaluation text, plot/table captions, summary and claim C1.6 explicitly disclose
   the post-preregistration exact-position OBJ seam recheck. Preregistered source
   snapshots and original rejects are retained.
2. `analyze_c1_pilot_v02.py` derives all acceptance counts and the manuscript table
   from `delivery_recheck.json`; original raw `accepted` fields are not aggregated.
3. The protection figure labels the rejected endpoints. Its figure plan, gallery
   caption and provenance call it a retained failed diagnostic. No failed A* path
   is drawn as an accepted output or executed robot trajectory.
4. PLUME is missing in numerical comparisons. Actual dependency and upstream API
   errors are retained and described as blocked applicability attempts.

C1.6 supports the reported corrected small pilot, with qualifiers. C1.9 broader
benefit remains unproven. Analytic fixtures support C1.7 only for their explicit
geometries. Policy navigation, real transfer and PLUME superiority remain
unsupported. The post-preregistration amendment is not erased by these responses.
