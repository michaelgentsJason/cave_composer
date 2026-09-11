Reviewed read-only. ICRA scope is okay on length: the live ICRA 2027 call says the complete paper limit is 8 pages including figures, acknowledgments, and references, and the current PDF is 7 pages. Source: https://2027.ieee-icra.org/contribute/call-for-icra-2027-papers-now-accepting-submissions/ ([2027.ieee-icra.org](https://2027.ieee-icra.org/contribute/call-for-icra-2027-papers-now-accepting-submissions/))

**CRITICAL**

- Visible TODOs and result placeholders remain in the submitted PDF path. Locations: `overleaf/sections/related_work.tex:36`, `overleaf/sections/platform.tex:66`, `overleaf/sections/evaluation.tex:138`, `overleaf/main.tex:30`, `overleaf/tables/navigation.tex:12-15`. This is fine for the working draft, but submission-blocking. Fix by converting TODOs into ordinary limitation/protocol prose, and either omit Table II or label it unmistakably as a protocol matrix until imported receipts exist. No new full RL run is needed as the fix for this review round.

- Current Overleaf figure tree still contains unreferenced private real-source preparation material: `overleaf/figures/generated/c1_v02/real_source_preparation.*`, plus source names in `overleaf/figures/generated/c1_v02/composition_provenance.json:22-25,30`. This conflicts with `overleaf/FIGURE_PLAN.md:62-63` and `overleaf/COMPLIANCE.md:38-40` if the source package includes the whole tree. Fix by whitelisting only referenced figures for the ZIP and excluding private provenance/images.

**MAJOR**

- `overleaf/sections/introduction.tex:48-49` says “The learning experiments assess…”, which reads as executed work. The ledger has C2.4 as `not_run` (`overleaf/CLAIM_EVIDENCE.yaml:190-199`), and `evaluation.tex:96-97` says no policy result exists. Fix: “The planned learning protocol is designed to assess…” or equivalent.

- `overleaf/sections/introduction.tex:39-41` says “preselected local real-source tasks,” but C3 eligibility is unresolved and the ledger says no scheduled episodes until gates pass (`overleaf/CLAIM_EVIDENCE.yaml:329-331`). Fix to “candidate local real-source tasks to be selected after eligibility and scale checks.”

- Related work is still too thin for review. `overleaf/sections/related_work.tex:1-37` has only PLUME, domain randomization, Isaac Lab, FlashSAC, and PPO, plus a visible TODO. Fix with verified citations for task-conditioned procedural environments, underground/cave navigation benchmarks, underwater visual simulation, and environment validation/sim-to-real. Keep the current careful positioning against PLUME.

- The protection formula needs one extra assumption. `overleaf/sections/method.tex:33-44` takes `max{F_var(x), rho_g - d_C(x)}` while also saying the field is not an exact signed distance. Fix by stating whether `F_var` is distance-like and in the same units, or rewrite the equation as an implementation rule whose guarantee comes only from final-mesh checks.

**MINOR**

- “physical full-exit tasks” at `overleaf/sections/evaluation.tex:84` and `overleaf/CLAIM_EVIDENCE.yaml:297-298` can sound like physical-robot execution. Use “geometric entrance-to-exit aperture tasks” or “portal full-exit tasks.”

- `overleaf/main.tex:27-29` mentions Isaac sensor frames, but the current main PDF references only Fig. 1-4 and does not include `isaac_stereo_actual`. Remove that sentence or make it conditional on including the figure.

- `overleaf/refs.bib:8` triggers `Warning--string name "sept" is undefined`. Change `month=Sept` to `{September}` or a BibTeX-supported month macro.

- Ledger labels use “Table A/B” while the manuscript uses IEEE Table I/II: `overleaf/CLAIM_EVIDENCE.yaml:143,201,235`. Replace with `tab:generator` / `tab:navigation` or descriptive names.

- Build preview PNGs are stale/missing page 7: `pdfinfo` reports 7 pages, but existing page renders are only 1-6 and older than `main.pdf`. Rerender final page previews after compile so visual review uses the current PDF.

No material mismatch found in the core C1/C2 evidence: the C1 table matches `summary.json`, PLUME is correctly reported as blocked rather than inferior, the post-preregistration OBJ seam recheck is disclosed, the 8-asset/24-task C2 count is supported via `episodes.json`, and the Isaac Sim smoke test is properly scoped as two static direct-USD instances with no Lab/vehicle/policy claim.
