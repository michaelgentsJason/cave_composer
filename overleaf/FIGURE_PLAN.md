# Editable figure drafts and required assets

The two overview schematics use the requested **figures4papers/scientific-figure-making**
workflow, with local design-theory/API guidance. They are deterministic
Matplotlib schematics, editable SVG text and vector PDF; PNG is 300 dpi.
Source: `figures/src/render_figures.py`. No image-generation model or synthetic
experimental screenshots are used. The palette remains distinguishable by
line style, layout and text, not color alone.

## Generated cave showcase (`fig:cave-showcase`)

The Introduction includes the existing hard_005 showcase as a double-column
qualitative example. The PDF is copied byte-for-byte from
`docs/figures/showcase_hard_v02/figures/cave_showcase.pdf` in the repository into
`figures/showcase_hard_v02/cave_showcase.pdf` for a self-contained paper folder.
The adjacent `provenance.json` records its hash, source scene and interpretation.

Twelve registered Blender Cycles interior views surround a mesh-sampled overview.
Red markers locate the cameras; yellow lines are construction centerlines.
The designed layout contains two rejoining loops and two blind branches, with
rocks and checkerboard props. Inspection lighting has no participating water
medium. This historical qualitative example is not a new pilot request, a
sensor reconstruction, an executed trajectory or a policy result.

## Cave Composer method overview (`fig:method`)

Conditions/seed/envelope → routes and chambers → varied protected geometry →
independent occupancy search → final visual/collision inside and clearance
checks → textured asset/task pack. Endpoint sampling is a separate input to
search. Construction routes do not supply the planner's solution. Failure
records are retained. An optional export/portal/props branch carries separate
changed-surface checks; its scope must not inherit closed-mesh inside checks.

The diagram's protected section and formula are explanatory. A construction
route and a geometric witness are not robot trajectories. Actual texture
appearance is described at the material/output stage; images are not evidence
of geometric validity. The renderer source and PDFs are available now.

## Navigation evaluation architecture (`fig:framework`)

Composer → Blender offline processing → Isaac Lab on Isaac Sim → distinct cave
instances → alternative FlashSAC or recurrent visual PPO runs → frozen
checkpoint → unseen generated full-exit tasks and eligible real-source local
tasks. Each baseline run has one cross-cave policy. The different miniature
skeletons are genuinely different structures, not repeated images.

AC1/Insight9 → Metashape → source-role audit joins only the designated real
asset branch. Downloaded scans go through the same audit. Final OOD has no
feedback to training. Actor inputs are pending and privileged maps/paths are
explicitly separate. Dashed blocks require external execution evidence.

## Asset inventory

| Needed item | Current material | Status / rule |
|---|---|---|
| Method geometry schematic | renderer source, generated SVG/PDF/PNG | available; illustration only |
| Exact final-mesh evidence | claim C1.2–C1.4 raw records | available for named versions only |
| Real cave appearance example | existing showcases | optional; keep its source and version; not Isaac runtime |
| Isaac heterogeneous-instance screenshot | two actual v02 static instances, stereo frames | available locally; no Lab/vehicle/policy claim |
| Imported collider/reset/camera evidence | final_rig_and_portals receipt | two direct-USD static cases only; remaining integration pending |
| Policy trajectory/learning curve | none supplied | **placeholder**, no plotted synthetic results |
| Real-source provenance | private source registry | incomplete use/scale/license fields; no new OOD inspection |
| Result / protocol tables | `tables/generator.tex`, `tables/navigation.tex` | C1 script-derived corrected pilot; C2/C3 policy results absent |

For final publication, align each result figure with a raw result manifest and
checkpoint/dataset hashes. Render all paper pages and inspect at final print
width. Detailed bookkeeping belongs in the text and repository, not more boxes.

## Actual figure material v02

`figures/generated/c1_v02/` adds quantitative pilot, fixed mesh cases, matched
clay/textured interiors, protection-failure geometry, actual Isaac stereo frames,
and prior real-source crop preparation. Editable SVG, PDF, PNG and source hashes
are retained. Quantitative, fixed-case and protection diagnostic figures are
in the main manuscript; other figures are reusable local material. The protection
panel includes a retained FAILED diagnostic scene and no policy trajectory.
The real-source preparation figure is private working material with unresolved
scale/source eligibility; exclude it from the anonymous Overleaf import package.
