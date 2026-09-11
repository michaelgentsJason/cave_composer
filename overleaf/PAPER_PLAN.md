# Paper plan and next evidence

**Question.** Can explicit navigation conditions produce controllable, varied
caves with independently checked final geometry, and does training on that
environment family improve navigation under a fixed learning system?

**C1 is primary.** The contribution is the coupling of conditions, protected
geometric variation, independent search and final artifact/task verification.
A*, surface extraction, batch generation and procedural textures are established
components. A larger or more attractive cave alone does not establish the claim.
**C2 supports C1:** external Isaac Lab integration and controlled heterogeneous
training, with one policy per algorithm/configuration/seed. **C3 tests value:**
frozen-policy local tasks in eligible real-source geometry under simulation.
Neither learning improvements nor physical sim-to-real are current results.

The [claim ledger](CLAIM_EVIDENCE.yaml) is authoritative; this outline does not
duplicate or upgrade evidence statuses. Historical task packs and later
morphology examples have different source hashes despite the same package label.

## Sections and intended space (eight pages total)

| Part | Purpose | Approximate final budget |
|---|---|---:|
| Abstract + introduction | Problem, coupled C1 mechanism, supporting C2/C3 | 1.0 page |
| Related work | Verified generator, randomization, platform and learning context | 0.6 |
| C1 method + Figure 1 | Conditions, protection, independent search, export scope | 2.0 |
| C2 platform + Figure 2 | Heterogeneous scenes, observations, delivery boundary | 1.0 |
| Evaluation + two tables | Generator mechanism evidence, matched navigation studies | 2.0 |
| Limitations + acknowledgment + references | Boundaries, AI disclosure, sources | 1.4 |

This is an allocation target, not permission to squeeze fonts. The current
shorter draft retains TODOs and empty result cells until experiments exist.

## Next round, ordered by impact on C1 credibility

1. **Measure the validator after artifact changes.** Define an explicit matrix
   of closed native, open portal, simplified collision, portable reimport and
   obstacle-added variants. Pin each mesh, task and check type. Inject blocked
   passages, visual/collision disagreements and export-transform errors into
   dedicated test copies. Measure missed failures and false rejection with an
   independently justified reference; do not count the checker as its own oracle.
2. **Run matched, multi-seed C1 studies.** Freeze requests, seeds, hardware and
   budgets. Compare restricted/full generation, protection off, morphology
   factors off and validation off as distinct interventions. Include all failed
   attempts in yield/cost denominators. One scene seed with six variants cannot
   support a distributional claim. Record requested and realized section,
   curvature, verticality, branch/dead-end and clearance distributions.
3. **Quantify accepted-set bias and realism on development sources only.**
   Separate route-biased endpoint selection from occupancy reachability. Measure
   what rejection removes, sensitivity to robot radius and grid resolution,
   and wall/section nonstationarity. Use existing development groups; do not
   inspect final OOD content to choose generator parameters. A photo depth
   histogram is not a measured cave-width distribution.
4. **Establish the external runtime boundary before training comparisons.**
   Confirm actual actor/action/frame/dynamics settings, active data hashes and
   different imported caves. Check collision cooking, coordinate transforms,
   camera pairs, reset/goal placement and simulated exit crossing per asset.
   Release a new immutable training version only after these checks. Compare
   limited versus full environments inside each learner at matched budgets.
5. **Resolve real-source eligibility and metric scale, then freeze C3.**
   Obtain source identities/licenses and use history for all intended assets,
   including the unconfirmed fifth Sketchfab model. Calibrate scans; account for
   holes. Long/short splits of a training cave are spatial holdout, not untouched
   cave transfer. Fix local tasks before outcomes, then freeze checkpoint,
   preprocessing, normalizer and inference rule with no in-episode intervention.

No new RL job is launched in this workspace round. Actual vehicle/Lab runtime,
training metrics and policy outcomes must come from the collaborator's platform.
The local two-static-instance Isaac Sim smoke is recorded separately below.

## Executed v02 evidence (separate from old training)

Six paired requests / 18 attempts, declared OBJ seam checker amendment, analytic
fault tests, 8-asset/24-task frozen handoff, and two-instance Isaac Sim smoke
are complete. Refer to the unique CLAIM_EVIDENCE entries C1.6--C1.9, C2.5--C2.6.
Do not call this a sufficiently powered external benchmark or a fully
clearance-matched policy study. C1.9/C2.3/C2.4/C3.2 remain submission blockers.
Next: calibrated realized-section constraints and controlled acceptance bias;
working compatible PLUME runtime; matched scene/task clearance conditions;
colleague vehicle/Lab receipt; frozen policy experiments on eligible sources.
