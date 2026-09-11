# Front-matter rewrite: author notes

Date: 2026-09-11. Scope: Abstract, Introduction, Related Work, necessary
bibliography entries and a visible result-placeholder macro. This is an editorial
revision, not a new experiment or generator release. Existing edits were backed
up before this revision in `outputs/front_matter_v03/previous_overleaf.zip`;
`baseline_hashes.json` records the pre-edit implementation and paper sources.

## Claim–evidence decisions made before drafting

| Claim | Status | Evidence inspected | Treatment in the rewritten text |
|---|---|---|---|
| Configurable route structure, section variation, local morphology and spatially varying roughness | implemented | `cave_composer/spec.py`, `routes.py`, `field.py`, `morphology.py`; `overleaf/sections/method.tex` | State concrete controls. Do not turn nominal dimensions into measured constraints, intended graph topology into certified free-space topology, or plausible morphology into measured realism. |
| Generation reserves a passage for a spherical robot plus margin and voxel allowance | implemented | `cave_composer/field.py`: protected union; `planning.py`: radius and tolerance handling | Explain the purpose of protection. It is an implicit-field construction rule; discretized geometry still needs checking. |
| Each sampled task can receive a search that does not consume the construction centerline or semantic graph | implemented | `cave_composer/planning.py`: `_search`, `RobotPlanningSpace.plan`, `plan_navigation`; `tasks.py`; `pipeline.py` | Define independence at the planner input. Endpoints remain route-derived and occupancy comes from the generated field. Do not imply independent geometry reconstruction, external certification, or unbiased task sampling. |
| Candidate polylines receive inside and spacing-corrected clearance checks on both extracted meshes | implemented | `cave_composer/planning.py`: `certify_polyline`; `delivery_validation.py`; actual certificates in `outputs/c1_pilot_v02/delivery_recheck.json` | State geometric checks for a static spherical envelope on the checked mesh versions. Keep dynamics, perception and policy execution separate. |
| The small paired pilot exhibits both the effect and the limits of protection | demonstrated | `outputs/c1_pilot_v02/preregistration.json`, `results/*.json`, `delivery_recheck.json`, `summary.json`, `endpoint_audit.json` | Report the balanced descriptive observation: full 5/6, protection off 4/6, restricted 6/6 in Introduction. The Abstract uses a whole-result placeholder. Protection changes acceptance in one stress case; a severe case is rejected by full and protection-off. Six base requests, not 18 independent caves. No statistical superiority claim. |
| General effectiveness, realized controllability and acceptance/cost distributions | planned | The executed pilot above; `overleaf/PAPER_PLAN.md` identifies larger studies but supplies no new execution evidence | Use a whole-conclusion `RESULT-GEOM` placeholder for the broader evaluation. Do not imply a completed PLUME performance comparison. |
| Four injected faults and two controls have the expected outcomes | demonstrated | `outputs/c1_pilot_v02/faults/results.json` | Retain in Evaluation, not Abstract or the contribution list. These deterministic fixtures do not estimate arbitrary-mesh detection accuracy. |
| Portal cutting and portable reimport have separate geometry checks | implemented | `cave_composer/portals.py`, `exit_tasks.py`, `delivery_validation.py`; `scripts/freeze_c2_release_v02.py`; `exports/cavern_pretraining_v02/manifest.json` and asset-local receipts | Keep detailed ordering in Methods. Front matter scopes its check to the extracted visual/collision meshes; it does not silently extend the check through later modifications. |
| Two static cave instances actually ran in Isaac Sim | demonstrated | `outputs/cavern_round_v02/isaac_runtime/final_rig_and_portals/runtime_receipt.json` | Keep in Platform/Evaluation as integration evidence. Direct USD construction, reset, RGB and collision probes are not a vehicle, Isaac Lab or policy result, nor validation of all eight assets. |
| Stereo RGB is a supported observation interface; the final policy is RGB-only | implemented / unclear | `cave_composer/sensors.py` and task-pack rig records support the interface; `overleaf/sections/platform.tex` and handoff profile mark actor/action settings UNCONFIRMED | State the interface only when needed. Do not claim RGB-only, no privileged inputs, calibrated underwater optics, or a confirmed colleague training configuration. |
| Training on these environments benefits navigation within FlashSAC or recurrent visual PPO | planned | No completed policy receipts in the inspected evidence set; baseline/interface plans in `overleaf/sections/platform.tex`, `evaluation.tex` | Whole-conclusion `RESULT-NAV` placeholder. Existing learners evaluate environment design; no new RL method. |
| Frozen-policy transfer on eligible unseen real-source cave assets | planned / unclear | `research_workspace/source_registry_v02.yaml`; evaluation plans; no transfer outcomes | Whole-conclusion `RESULT-TRANSFER` placeholder. Source eligibility and scan scale are unresolved. Same-cave spatial holdout is not unseen-cave transfer; simulation in scanned geometry is not physical sim-to-real. |

## Narrative decision

The method is Cave Composer throughout the rewritten sections. The existing
title is retained, without explaining internal naming history. The argument
centers on relating cave variation to a finite robot's geometric task: reserve
space during generation, then check a searched task path against the generated
boundaries. This is a concrete system design contribution, not a claim to have
invented procedural generation, navigability validation or solvable environment
distributions. Downstream learning is an empirical question with explicit
result placeholders.

## Literature added and how it changes the argument

| Work / verified metadata | Primary source used | Use in the rewrite |
|---|---|---|
| Raistrick et al., Infinigen Indoors, CVPR 2024, 21783–21794, DOI 10.1109/CVPR52733.2024.02058 | [Author project and BibTeX](https://infinigen.org/), [full paper](https://arxiv.org/html/2406.11824) | Constraint language/solver and simulator export are existing capabilities; our controls focus on cave boundaries and robot clearance. |
| Yang et al., Holodeck, CVPR 2024, 16227–16237 | [CVF proceedings and BibTeX](https://openaccess.thecvf.com/content/CVPR2024/html/Yang_Holodeck_Language_Guided_Generation_of_3D_Embodied_AI_Environments_CVPR_2024_paper.html), [full paper](https://arxiv.org/html/2312.09067) | User intent, spatial relations and optimized asset placement connect controllability to embodied scenes. |
| Paris, Guérin, Peytavie, Collon and Galin, CGF 40(7), 277–287, 2021, DOI 10.1111/cgf.14420 | [Author publication and BibTeX](https://perso.liris.cnrs.fr/aparis/public_html/projects/paris2021_Karsts.html), publisher-deposited Crossref metadata | Establishes geological constraints, cave networks and implicit cross-section control as prior work. Author order follows the published record, not a conflicting preprint display. |
| Cano, Tardioli and Mosteo, IROS 2024, 4608–4615, DOI 10.1109/IROS58592.2024.10801552 | [IEEE publication/abstract](https://ieeexplore.ieee.org/document/10801552/), publisher-deposited Crossref metadata | Direct underground-robotics precedent: graph-to-mesh generation and automated simulation workflows. |
| Cobbe, Hesse, Hilton and Schulman, ICML 2020 / PMLR 119, 2048–2056 | [PMLR paper and BibTeX](https://proceedings.mlr.press/v119/cobbe20a.html) | Relates training environment distributions to sample efficiency and held-out performance. |
| Dennis et al., NeurIPS 33, 13049–13061, 2020 | [Official proceedings/BibTeX](https://proceedings.neurips.cc/paper/2020/hash/985e9a46e10005356bbaf194249f6856-Abstract.html), [full paper](https://arxiv.org/html/2012.02096) | PAIRED already addresses structured, solvable distributions; contrast policy-return-driven adaptation with explicit geometric conditions. |
| Song et al., OceanSim, IROS 2025 | [Author project and BibTeX](https://umfieldrobotics.github.io/OceanSim/), [full paper](https://arxiv.org/html/2503.01074) | Underwater visual/acoustic simulation is complementary platform functionality, not a Cave Composer contribution. No unverified page range or DOI was added. |

Previously cited literature was also checked where used:

- [ProcTHOR](https://arxiv.org/html/2206.06994), Appendix B.11: post-generation reachability validator with a planar grid and per-room reachable positions. Metadata follows the published NeurIPS record; the original arXiv author list differs.
- [Infinigen](https://arxiv.org/html/2306.09310), Appendix G.2.1: probabilistic rules include turns, elevation and forks; passages have varying cross-sections and are combined before meshing. This rules out portraying earlier systems as uniform pipes plus noise.
- [PLUME](https://arxiv.org/html/2508.20926), graph/mesh/texture sections: single/multiple layers, user-supplied graph, mesh generation, procedural materials, baking and simulator use. Its publication record remains a 2025 arXiv preprint in this bibliography.
- [Domain randomization](https://arxiv.org/abs/1703.06907) and its IROS DOI support the visual-transfer background, not a claim that Cave Composer has achieved transfer.
- [Stonefish](https://doi.org/10.1109/OCEANSE.2019.8867434) supports marine simulation context. Publisher-deposited metadata confirms author, venue, year and DOI.
- [Isaac Lab](https://arxiv.org/abs/2511.04831) supports the external robot-learning framework description, not the existence of our colleague's executed integration.
- [FlashSAC official RSS 2026 proceedings](https://www.roboticsproceedings.org/rss22/p099.html) verifies the title, complete author list and DOI. The existing shortened author list was completed. [PPO](https://arxiv.org/abs/1707.06347) names the underlying established method; it is not evidence of a particular recurrent visual implementation.

Local retrieval copies and publisher metadata are in
`outputs/front_matter_v03/literature/`. No oral/spotlight/award labels were used.
The Cano full text was not available through the accessed primary landing pages;
only capabilities explicitly stated in IEEE's abstract are attributed to it.
No absence of a robot-clearance mechanism is inferred from that access limit.
All newly inserted citations are resolved; no invented citation or hidden
`CITE-TODO` is used.

## Visible placeholders and the evidence needed to fill them

| Marker | Location | Required evidence |
|---|---|---|
| RESULT-NAV | Abstract and Introduction | An executed environment-design comparison **within each** baseline; exact actor observations/goal conditioning, learner implementation, matched budgets, scene/task versions, all scheduled episode outcomes, training seeds and uncertainty. Replace the whole instruction with an outcome of either direction. |
| RESULT-GEOM | Abstract and Introduction | An executed study with the tested geometric claim and comparison specified; independent scene/request groups distinguished from task repetitions and condition arms; requested vs realized geometry, accepted/rejected counts and cost with fixed budgets; uncertainty at the proper sample unit. A fair PLUME comparison requires an actual compatible run, not source inspection. |
| RESULT-TRANSFER | Introduction | Eligible and scale-resolved real-source assets with use history, exact local/full-exit task scope, frozen checkpoint/preprocessing/normalizer/inference conditions and all scheduled outcomes. State that this is simulation in reconstructed geometry unless physical robot trials actually exist. |

These three types appear five times. They replace unknown conclusions, not only
unknown numbers. There is no prewritten improvement, superiority or successful
transfer. No `EVIDENCE-TODO` is needed in these sections because unverifiable
mechanisms were omitted or narrowed; unresolved implementation questions are
listed below. Other sections retain their pre-existing TODO/UNCONFIRMED text.

## Important information removed from the front matter, without losing evidence

| Information | Where it belongs / existing retained location |
|---|---|
| 18 attempts / six paired base requests; no retries; four normal and two stress requests; full 5/6, protection-off 4/6, restricted 6/6 | Evaluation, generator table and `outputs/c1_pilot_v02/`; keep all denominators and the non-positive comparisons. The Introduction retains all three denominators and the two stress-case outcomes; the Abstract uses a whole-result placeholder for the broader geometric study. |
| OBJ seam-incidence correction and original import rejections | Evaluation's explicit correction paragraph; original `results/*.json` plus `delivery_recheck.json`. Do not silently delete first-pass rejections or describe a changed importer as new geometry generation. |
| Four analytic faults / two controls | Evaluation's fault paragraph/table and `outputs/c1_pilot_v02/faults/results.json`; describe fixture scope. |
| Eight frozen assets, fixed internal/full-exit tasks and hashes | Platform/Evaluation and `exports/cavern_pretraining_v02/manifest.json`; ordinary packaging is not an independent major contribution. |
| Two-instance Isaac Sim smoke test, direct USD construction, reset/RGB/collision probes and corrected lighting attempt | Platform and actual runtime receipt; integration evidence, not navigation learning. |
| Portal-cutting sequence, open-surface crossing check, portable reimport and per-version mesh/path binding | Methods, export protocol and asset receipts. Closed-reference acceptance does not automatically cover changed geometry. |
| CAVERN/Cave Composer naming history; C1/C2/C3 contribution priorities | Naming history removed. Internal coordination may retain work-package names; paper title unchanged. |
| PLUME source comparison and failed local runtime attempts | Experimental plan / author notes, not Related Work. `outputs/c1_pilot_v02/external/plume/attempts.json` and the external-graph attempt distinguish native dependencies and Blender API compatibility failures from algorithm outcomes. |
| Proposed observations/actions, RGB-only ambiguity, actual colleague configuration | Platform and collaborator handoff; final actor input is not inferred from an RGB render. |

## Technical and evidence questions that prose cannot settle

1. **Strength of novelty and general effect.** The design is a particular coupling
   of established ideas. A small pilot cannot establish distribution-wide
   controllability, better realism or superiority to the closest generators.
   Realized clearance differs between full and restricted geometry; this can
   confound downstream comparisons unless it is controlled or explicitly measured.
2. **Geometric scope.** The envelope is a static sphere. The mathematical
   distance bound assumes valid boundaries/exact distances; the implementation
   uses floating-point distances, parity and an engineering tolerance. Closedness
   and winding checks do not independently rule out every self-intersection.
   Search failure is not a proof that every continuous path is infeasible.
3. **Independence and sampling.** Search is independent of the construction route
   as an input, not of the generator's occupancy representation or route-derived
   endpoint distribution. No global topology or unbiased task-distribution claim
   is supported.
4. **Order and geometry identity.** Generation and extraction -> closed-reference
   search/checks -> optional portal cutting -> open-surface path/crossing checks
   -> portable export/reimport checks -> separate simulator import/runtime checks.
   Some delivery scripts explicitly recheck artifacts, but no general certificate
   covers arbitrary scaling, collider cooking, scene modifications or imports.
5. **Navigation platform.** The runtime receipt is explicitly `isaaclab_tested:
   false`, static geometry and diagnostic RGB, with no vehicle/controller/RL.
   Actual observations, localization assistance, action definition, dynamics,
   baseline implementations and training manifests still need platform evidence.
6. **Held-out sources.** Referenced CAVERS/Sketchfab appearance sources have
   development/prior use. Source identity/use history and Metashape metric scale
   remain unresolved for transfer eligibility. Long/short crops of one cave are
   spatial holdouts, not different physical caves.
7. **Outside this edit's scope.** Method/Platform headings and Figure 2 still use
   C1/C2 workflow vocabulary; the latter still emphasizes a planned framework.
   Later Methods/Platform/Limitations paragraphs retain progress-report language.
   These deserve a later scoped edit. They were not rewritten here. The title
   still uses CAVERN while the three rewritten sections consistently introduce
   Cave Composer, as explicitly permitted by the request.

## Compilation and review

Initial compilation succeeded with pdflatex, BibTeX and two final pdflatex
passes. Figure scripts were not run. Final checks below use the post-review PDF, not the initial build.


### Cross-review disposition

A fresh GPT-5.5 xhigh reviewer, invoked through ARIS paper-write Step 6, judged
the rewrite a scientific argument with targeted corrections, not a project audit.
Full local response: `outputs/front_matter_v03/reviewer_response.md`.

- Addressed the abstract's overly qualitative pilot wording by moving precise
  denominators to Introduction and using RESULT-GEOM for the broader abstract
  conclusion. This follows the user's permission for whole-result placeholders
  and avoids rebuilding the old abstract's experiment-count inventory.
- Changed the baseline sentence to a conditional evaluation use; changed the
  Related Work platform paragraph to describe complementary capabilities and
  evaluation requirements without asserting executed integration.
- Cleaned the source line break and BibTeX whitespace noted by the reviewer.
- Did **not** add the proposed third contribution for a retained-failure protocol:
  the user explicitly asked not to elevate routine records or planned protocols
  into an additional major contribution. The initial rewrite retained two methodological contributions. The subsequent
  user-directed revision below restores the three-part paper-level claim chain;
  executed pilot details remain available in Evaluation.
- Retained the unused CERBERUS BibTeX entry to avoid removing an existing
  reference unnecessarily. It is not printed by BibTeX; it adds no paper length.

Final self-review: the front matter identifies Cave Composer, motivates task-aware
cave variation, states a concrete connection to the closest prior work, separates
the two implemented mechanisms within the generator contribution, reports the
pilot at its actual sample unit and
marks all broader geometric/navigation/transfer conclusions as awaiting results.

### Final delivery checks

- Rewritten source: `overleaf/sections/abstract.tex`, `introduction.tex`,
  `related_work.tex`; necessary changes: `overleaf/refs.bib`, `overleaf/main.tex`.
  Main changes only by adding `\resultplaceholder`; conference template and title
  are unchanged. Seven bibliography entries were added; FlashSAC authors and
  month formatting were cleaned using verified metadata.
- Readable full text: `research_workspace/FRONT_MATTER_v03_REWRITTEN_TEXT.md`.
  Abstract: approximately 173 English words including visible placeholder text.
- Compiled PDF: `overleaf/build/main.pdf`. Final pdflatex/BibTeX/pdflatex/pdflatex
  passes all exited successfully; logs are `outputs/front_matter_v03/compile_final_*.log`.
- **9 pages including references**, versus the existing paper plan's **8-page**
  target. Page 9 contains a short bibliography continuation. This is a working
  draft, not an eight-page submission-ready artifact. No fonts/margins were
  compressed to conceal the length.
- **0 undefined citations, 0 undefined references, 0 overfull boxes.** Fifteen
  bibliography entries are cited and printed. One unused pre-existing entry is
  retained only in the BibTeX source.
- Five visible placeholders were verified in extracted PDF text: RESULT-GEOM
  twice, RESULT-NAV twice, RESULT-TRANSFER once. All fonts are embedded; no Type 3
  fonts. The first three pages and bibliography continuation were rendered and
  visually inspected; no clipped text, overlapping content or missing symbols
  were observed in the inspected pages.
- Remaining TeX diagnostics: two underfull hboxes (second contribution and PPO
  bibliography entry) and one underfull vbox in the unchanged Methods/Platform
  float flow. They indicate loose spacing, not overflowing content. The first
  method figure now appears later because of existing float placement.
- To return to the eight-page target in a **later authorized full-paper edit**,
  compress the duplicate status/history prose in Method/Platform, place
  integration/fault-fixture implementation detail in reproducibility material,
  and reconsider existing figure placement. Retain all failure/correction facts.
- Scope check compared 151 pre-edit code/config/paper files and the entire
  backed-up non-build Overleaf tree. Only the five allowed manuscript/bibliography
  sources changed; generator/RL code, other sections, existing figures and user
  changes were preserved. No training, asset generation or new experiment ran.
- Machine-readable receipt: `outputs/front_matter_v03/verification.json`;
  exact source diff: `outputs/front_matter_v03/front_matter.patch`.

## Follow-up: three paper-level contributions

Following the user's clarification, the contribution list now follows the
paper-level chain: (1) controllable cave generation **including** passage
protection and per-task geometric verification; (2) the measured navigation
effect of training-cave diversity within fixed existing learners; (3)
frozen-policy outcomes on eligible unseen real-source cave assets in simulation.
The previous two entries decomposed only the generator contribution.

Items 2 and 3 are complete visible RESULT-NAV / RESULT-TRANSFER placeholders,
not claims of completed studies or predetermined improvements. Their duplicated
placeholders immediately before the list were removed; the total remains five
visible result placeholders across Abstract and Introduction. The paper does
not acquire a new RL method or an original underwater simulator through this
reorganization. The readable full text was synchronized.

Follow-up build and scope receipt: `outputs/contributions_v03_followup/verification.json`.
The v03 build receipt above describes the previous PDF snapshot.
