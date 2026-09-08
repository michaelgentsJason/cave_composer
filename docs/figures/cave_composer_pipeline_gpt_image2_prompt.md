# Cave Composer 方法图：GPT-image2 prompt

用途：论文双栏通栏的方法总览图。下方英文代码块可直接复制给 GPT-image2。
本文件只提供绘图指令，不将生成式示意图当作真实实验截图。

建议画布比例 2.15:1，尽可能高分辨率；最终排版宽度约 180 mm。
图中文字用英文，说明放论文 caption 中。优先保证缩小后的可读性。
如要放真实洞穴，提供本文末尾列出的真实渲染作为参考，并在最终排版时嵌入原图。

## 可直接复制的完整 prompt

```text
Create a publication-quality robotics METHOD OVERVIEW FIGURE for a research
paper about “Cave Composer”, an automated, controllable cave environment
generator for robot navigation. The intended visual quality is that of a
carefully designed ICRA / RSS / CoRL paper figure. This is a scientific
explanation, not a marketing infographic, application screenshot, or poster.

SCIENTIFIC MESSAGE
Show how explicit navigation-related conditions become varied cave geometry,
and how the resulting navigation task is checked on the final meshes before
the scene is exported. Make the coupling between geometric variation and
robot clearance the conceptual focus. The independent planner must visibly
consume occupancy plus endpoints, not the construction centerline.

CANVAS AND COMPOSITION
- Landscape canvas, aspect ratio approximately 2.15:1, white background.
- Design for a two-column-wide paper figure, approximately 180 mm wide in print.
- Use the highest supported native resolution. Keep all text crisp.
- Outer margins: 3% of canvas width. No large title banner; the caption will
  provide the title in the paper.
- Main row occupies approximately the top 60% of the canvas. Arrange exactly
  five stages from left to right, labeled (a), (b), (c), (d), (e).
- Give stages (c) and (d) more width than (a), (b), and (e). Suggested width
  proportions excluding gutters: 15%, 18%, 24%, 25%, 18%.
- Bottom row occupies approximately 30% of the canvas and contains two
  explanatory insets: a cross-section under (b)-(c), and a validation inset
  under (d)-(e). Reserve the remaining space for gutters and a compact legend.
- Use subtle grouping outlines, consistent corner radii, and ample whitespace.
  Prefer explanatory miniatures over stacks of text boxes.
- A restrained axonometric cave miniature is appropriate for geometry data;
  pipeline boxes, arrows, and typography must remain flat and clean.

EXACT MAIN STAGES

(a) “Task conditions”
Draw one compact specification card with only these four readable lines:
  “Turns & slope”
  “Width & height”
  “Topology”
  “Robot radius + margin”
Place “Config + seed” as a small header or input label.
Add a small schematic sphere with a dashed outer safety ring. Do not use a
humanoid, wheeled rover, or detailed underwater vehicle: the current geometric
validator uses a spherical envelope and is platform-independent.
Output arrow from (a) to (b): “Structure parameters”.

(b) “Structure grammar”
Show a clean plan-view semantic cave skeleton with several bends, one branch,
and one chamber marker. Use a cyan solid line for the construction route.
Place a small start circle S and a goal diamond G at different ends.
Include four compact structure glyphs below it, labeled:
  “Winding”, “Branching”, “Loop”, “Chambers”.
Glyphs should actually differ in their topology and layout, not merely color.
Add a small secondary note: “Bounded layout screening”.
The semantic graph specifies intended structure. Do not imply exact recovery
or certification of the full free-space topology.
Output arrow from (b) to (c): “Routes + chambers”.

(c) “Clearance-aware geometry”
Make this a visually rich but restrained scientific miniature. Show the same
bent cave layout progressing from a translucent coarse void to an irregular
rock boundary. The central passage must remain visible through an explicitly
labeled local cutaway; do not depict the inspection cutaway as a missing roof
in the actual exported cave.
Use a translucent cyan volume around the construction route to indicate a
protected passage. Surround it with muted warm gray / sandstone rock. Vary
cross-sections and chamber contours; avoid uniform circular industrial pipes.
Show three short labels with clear leaders:
  “Protected passage”
  “Irregular sections”
  “Rock detail”
At the right edge, show two small representations of the SAME cave: a solid
surface labeled “Visual mesh” and a slightly coarser wireframe labeled
“Collision mesh”. Different triangle densities must not imply different cave
layouts. Use “Implicit void field”, not “Exact SDF”, in the small stage footer.
Output arrow from (c) to (d): “Final meshes + occupancy”.

(d) “Navigation verification”
Draw two visibly separate operations, connected in sequence:
  “Occupancy A*” → “Dual-mesh clearance check”.
The A* miniature should be a top-down occupancy grid with a bent open corridor,
gray occupied cells, white free cells, S and G, and a magenta dashed candidate
path. Allow the candidate path to differ from the cyan construction route.
The actual planner searches a 3D occupancy grid; label this miniature
“Schematic slice” so the drawing does not suggest the method is only 2D.
Place a small label next to the A* input:
  “Occupancy + S/G only”.
There must be NO arrow feeding the semantic graph or construction centerline
directly into A*. The generator's centerline is not the planner's answer.
The clearance-check miniature should show the candidate path passing through
the actual rock mesh and a spherical robot envelope separated from the wall.
Use two modest check marks beside “Visual” and “Collision”. They indicate
per-scene validation, not a universal guarantee of success.
Only the successful branch goes to stage (e), with arrow label “Validated”.
Route a thin dark red dashed failure arrow downward into a small box labeled
“Failure record”. Do not loop this arrow back as an automatic repair or learning
loop: failed scenes are recorded; the depicted system is not self-optimizing.

(e) “Reproducible scene sets”
Show three small, different cave miniatures grouped as a dataset, followed by
compact output labels:
  “Meshes + materials”
  “Graph + S/G + path”
  “Metrics + provenance”.
Below the miniatures place split labels:
  “Train / ID”
  “Geometry OOD”
  “Composition OOD”
  “Topology OOD”.
Use a two-loop glyph only in the “Topology OOD” example. The current training
families include winding, branching, single-loop, and chambers. These labels
describe configured split rules, not a claim of proven policy generalization.

LOWER LEFT INSET: “Geometry variation with a protected passage”
Draw a large 2D cross-section of an irregular cave wall. The free cavity is
white, the surrounding rock is muted beige, and a translucent cyan disk
indicates the protected generation region.
At its center show a smaller sphere / circle representing the robot, with a
dashed outer ring for its safety margin. The generation protection disk must
be visibly larger than robot + margin, because the generator also includes a
voxel discretization allowance. Label it “Including voxel allowance”.
Use two small boundary profiles, or restrained arrows, to show wall variation
outside the protected core. A rock protrusion may approach the protected
region, but must not cut through the protected passage.
Do not imply the entire navigable cavity is cylindrical or globally convex.

LOWER RIGHT INSET: “Checking between samples”
Show a short magenta polyline inside an irregular rock passage, with several
sample points and a wall-distance segment. Make clear that checking only
discrete points is insufficient, so a spacing allowance is subtracted.
Include exactly this compact formula if the renderer can typeset it cleanly:
  “d_min − h/2 > r + m”
Small adjacent labels:
  “h: maximum sample spacing”
  “r + m: required radius”.
Add “Inside checks on closed reference meshes” underneath in secondary text.
This is a numerical geometric certificate along the checked polyline, using
the 1-Lipschitz property of distance; it is not a new planning algorithm, a
kinodynamic proof, or proof that every possible task in the cave is solvable.

SECONDARY APPEARANCE INPUT
Below or beside stage (c), place one small sandstone texture swatch labeled
“Appearance seed”. Connect it to the materials output using a thin secondary
line routed around, never through, the verification stage.
Optional tiny note: “Optional CAVERS color prior”. This represents a color
prior from real observations, not imported scanned cave geometry, a learned
generative model, or a reconstructed physically accurate material.

OPTIONAL PORTAL EXPORT NOTE
If space permits, a small dashed box AFTER successful validation may read
“Optional entrance / exit export”. Show two uncapped terminal apertures and
label the result “Open surface”. This is a separate deterministic export step
with its own boundary and crossing-path checks. It must not be shown as part
of the historical v0.3 closed-mesh validation certificate. Omit this secondary
box if it makes the figure crowded. S/G markers alone do not mean physical
entrance and exit openings.

COLOR AND GRAPHIC SYSTEM
- Text and arrows: charcoal #273444.
- Construction route and protected region: teal #168C9E / pale teal #DDF2F3.
- Independently searched path: magenta #B64282, dashed stroke.
- Rock geometry: muted sandstone #C9B297 with subtle neutral shading.
- Successful checks: dark green #397B58. Failures: muted red #A65454.
- All other borders and occupancy cells: light neutral gray.
- Keep the palette restrained. Meaning must survive grayscale printing:
  route is solid, independent path is dashed, start is a circle, goal a diamond.
- Main flow arrows: dark, consistent, approximately 1 pt at print size, with
  clear arrowheads. Avoid crossing arrows and ambiguous merging lines.
- Use Arial/Helvetica-like typography, consistent capitalization, and short
  labels. Main stage labels about 10–11 pt at print size; secondary labels
  8–9 pt. No tiny paragraphs. Preserve all required labels without crowding.

STRICT EXCLUSIONS
No performance bars, percentages, training gains, “SOTA”, “first”, “optimal”,
“guaranteed real-world navigation”, or comparisons claiming PLUME is worse.
No neural network, diffusion model, LLM module, learned terrain generator,
erosion simulation, arbitrary recursive multilevel network, or dynamics engine.
No Stonefish / Gazebo / Isaac logos or simulation screenshots. No RL training
loop: the current figure is about the standalone generator and its outputs.
No sealed cap drawn across an aperture labeled entrance or exit. No exterior
shortcut presented as an in-cave navigation solution.
No glossy gradients, glow, heavy shadows, decorative robots, rainbow palette,
stock icons, illegible code snippets, or dashboard-like panels.
Do not invent experimental images. Any rendered cave miniature produced here
is a METHOD SCHEMATIC; measured results belong in separate figures.

FINAL COMPOSITION CHECK
At a glance the reader should understand five things: explicit task conditions;
varied cave structures; protected clearance during geometric variation;
independent search followed by final-mesh verification; reproducible scene
sets with controlled split definitions. Spend visual detail on the cross-section
and validation mechanism. Keep routine packaging details secondary.
Return one clean, complete figure on a white background.
```

## 建议 caption

**Cave Composer overview.** Structured scene conditions and seeded grammar
sampling define routes and chambers. An implicit void field combines a
protected passage with irregular cross-sections and rock detail, and produces
separate visual and collision meshes. A clearance-weighted A* search uses
collision occupancy and task endpoints without access to the construction
centerline. Candidate paths undergo inside and continuous-clearance checks on
both final closed meshes before validated scene bundles are exported with
navigation annotations, provenance, and configured ID/OOD splits. Appearance
randomization is controlled separately. Illustrations are schematic; the
clearance evidence applies to a spherical robot envelope along the checked path.

若保留 portal 小框，在 caption 末尾加：
“An optional subsequent export opens terminal portals and checks their boundaries
and the crossing path; it is recorded separately from closed-reference validation.”

## 真实参考图与核对要点

- 内部纹理：`outputs/pipeline_v03_final/chambers/scene_000001/previews/inside_02.png`
- 整体结构：`outputs/pipeline_v03_final/chambers/scene_000001/previews/overview.png`
- 实际路线：`outputs/pipeline_v03_final/chambers/scene_000001/previews/topology.png`
- 不把生成用中心线直接接入独立 A*。
- 保护区包含离散化余量，不能把它标成恰好等于机器人半径。
- 标注“隐式场”，不标成精确 SDF；回环数是语义图性质，不代表所有自由空间拓扑已被证明。
- 用示意图讲机制；真实效果图、统计图使用真实渲染和实验文件。
- GPT-image2 输出为位图。投稿排版时核对文字、公式和箭头；需要可编辑文字时在矢量排版工具中重排。
