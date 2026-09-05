# V0 requirement audit

This audit covers the attached first-round objective and the follow-up requesting
local CAVERS appearance references. The final report is
[CAVE_COMPOSER_V0_REPORT](../CAVE_COMPOSER_V0_REPORT.md).

| Required outcome | Evidence | Status |
|---|---|---|
| Inspect workspace, shared assets and Blender | `architecture_v0.md`, `material_inventory.json`; shared Linux path absent on host/WSL, local Blender used | DONE, shared-asset availability limitation recorded |
| Compare representations before implementation | `architecture_v0.md`; independent checkpoint `7bf8111` | DONE |
| Structured grammar, explicit turns and variable sections | `specification.md`, `spec.py`, `routes.py`, eight angle tests | DONE |
| Layered geological geometry, separate nav/visual/collision | `field.py`, `export.py`, six scene bundles | DONE; morphology realism remains limited |
| Seeded, material-independent generation | Four serial/parallel matches; CAVERS four-file identity checks | PASS |
| Six visually different A–F | `outputs/final/gallery.html`; B revised after side-by-side review to distinguish it from C | PASS |
| Navigation metadata and actual geometry validator | Per-scene graph, clearance, visibility, validation and BVH audit files | PASS within documented offline sphere/polyline scope |
| Automated overview, inside and topology previews | Four PNGs and packed `.blend` per final scene | PASS |
| Inspect material type and prototype transfer | Initial asset inventory plus rock-only CAVERS RGB ROI experiment | DONE; palette inference works, measured PBR recovery incomplete |
| CAVERS read-only appearance reference | Two original SHA256 checks; sampled four sequences; baseline/restyle comparison | PASS |
| Avoid baked water and geometry copying | Procedural source provenance, material output and CAVERS experiment | PASS |
| Headless CLI, batch factory and parallel seeds | Python/Blender logs, batch manifests, installable wheel | PASS at smoke-test scale |
| Train/validation/ID/OOD composition contract | `dataset.py`, 250 sampled-config assertions across five splits; seed namespace disjointness | PASS; three generation splits exercised |
| Inspect PLUME only after independent prototype | `independent_checkpoint.json`, `plume_source_inventory.json`, `plume_comparison.md` | DONE |
| Final architecture decision | `architecture_final.md` | DONE |
| Research Stonefish mesh/material interface | Official-source citations in `stonefish_interface.md`; exported XML and adapter tests | DONE for this phase; runtime PARTIAL |
| Eleven-section final report with bounded claims | Root report, measured table and per-scene preview links | DONE |

The required v0 pass gate is satisfied by six distinct, parameterized, validated,
navigable, reproducible scenes with headless generation and actual visual previews.
The machine audit checks stored meshes against provenance, current validator
identity, regenerated collision evidence, image integrity, XML references,
complete bundle checksums, batch results and material experiment geometry identity.
Run `python scripts/verify_delivery.py` while the delivered local artifacts exist.
It is a workstation delivery audit, not the portable test suite.

Explicitly deferred under the first-round scope: runtime LLM parsing, fly-through
(optional), full geological process simulation, simulator execution/parallel robot
environments, learning, water/sensor/dynamics randomization and real OOD navigation.
Large-scale throughput and statistical failure-rate claims need new experiments;
they are not inferred from ten final-distribution scenes. Physical PBR recovery,
exact recovered topology and geometry-predicate proofs remain limitations.

No external messages, remote publication, source-scan edits, PLUME code copying,
RL training, or Stonefish modifications were performed. Public licensing remains
an owner decision for the later repository release.
