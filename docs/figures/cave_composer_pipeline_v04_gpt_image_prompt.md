# Cave Composer 方法图：精简版 GPT-image prompt

本版收敛为四个阶段：**可控生成 → 多任务采样 → 独立验证 → 任务与观测输出**。取消重复洞穴缩略图、嵌套边框、大面积双目面板，以及配置、文件和审计清单。

复制下面英文代码块给 GPT-image；可以同时附上上一版图片，作为需要简化的参考。

```text
Design a concise, publication-quality method figure for “Cave Composer”.
Use the visual restraint of a well-edited CVPR / ICRA / RSS paper: a clear
scientific idea, explanatory geometry, sparse labels, and generous whitespace.
If an earlier figure is attached, treat it as content reference only. Redesign
its composition completely; do not preserve its boxes or information density.

CORE STORY
Controllable cave geometry → multiple start–goal tasks within one cave →
independent path verification → reusable tasks and stereo RGB observations.
Make protected clearance and per-task verification the visual focus.

LAYOUT
- White background, landscape approximately 2.3:1, highest native resolution.
- Intended for 180 mm two-column print width.
- Four UNBOXED stages in one left-to-right row, labeled (a), (b), (c), (d).
  Width proportions approximately 32%, 20%, 30%, 18%, excluding gutters.
- Align stage headings. Use thin arrows between stages.
- Reserve roughly the bottom quarter beneath (a)–(c) for ONE compact mechanism
  detail, without an enclosing panel. No second full-width row.
- Preserve approximately 25% whitespace. No title banner, dashboard panels,
  tinted label backgrounds, nested cards, or thick outlines.
- Keep total visible text under 110 words, including labels and legend.
  Only render the explicitly quoted labels below and the specified notation.
  The explanatory instructions are not text to place in the image.

(a) “Controllable generation”
Above the main miniature, use one quiet input line:
“Topology · Shape · Clearance · Seed”.

Show a small teal skeleton transitioning into ONE larger irregular cave.
Use a bent main passage, a rejoining side passage, and an enlarged chamber.
Keep its silhouette recognizable in subsequent stages.
The skeleton is a simple line drawing, not another shaded cave rendering.

The main cave has muted sandstone walls and a pale teal protected passage.
Use a local opening in the drawing to reveal the interior; label it “Cutaway”.
This is an inspection illustration, not a physically missing roof.
Use one leader label: “Protected passage”.
Vary wall shapes and cross-sections; avoid uniform tubes and exaggerated rubble.
No topology-glyph gallery, separate texture swatch, or three mesh copies.

(b) “Task sampling”
Draw ONE flat plan-view outline of the same cave, simpler than stage (a).
Place two distinct S/G pairs within it: S₁/G₁ and S₂/G₂. Start markers are
circles, goal markers are diamonds. At least one goal lies inside the side
passage, away from its junction. Numeric subscripts associate pairs.
Do not draw planned paths in this sampling stage.
One annotation: “One cave, multiple tasks”.
No repeated cave stack, taxonomy, episode cards, or task-count badges.
The outgoing arrow to (c) is labeled “S/G pairs”.

(c) “Independent verification”
Show ONE occupancy-grid miniature of the same layout: occupied cells in
light gray, free corridor in white. Select one sampled pair and draw its
independently searched path as a magenta dashed line.
Label the operation “3D A*” and the view “Schematic slice”.

The planner has two visible data inputs: “S/G pairs” from (b), and
“Occupancy” from (a). Route the latter along a thin line above the stages.
No semantic skeleton or construction centerline may feed directly into A*.
Omit a decorative centerline overlay in the grid.

Below the grid, use a small downward arrow leading to “Dual-mesh check”.
Under this label, place two modest green checks: “Visual” and “Collision”.
These denote checks on both final meshes for the illustrated task.
Do not add another full cave rendering here.
Bring a thin secondary connector from (a), labeled “Final meshes”, directly
to this check. Route it through the whitespace below the main row, above
the mechanism detail, without crossing other arrows.

The output arrow to (d) must originate AFTER the dual-mesh check, never from
the A* grid. Label it “Accepted”.
A tiny muted-red dashed offshoot from the verification stage terminates at
“Failures logged”. No large failure box, retry loop, or repair loop.

(d) “Tasks + observations”
Use a lightweight schematic stack of two task sheets, with just the label
“Verified tasks”. No file-list boxes or database icons.
Below it, show a small paired image example labeled “Left RGB” and “Right RGB”.
The images depict the same cave with consistent texture and lighting and
plausible horizontal parallax. Keep them subordinate to stages (a) and (c).
Label the pair collectively “Stereo RGB”. No physical camera rig,
calibration table, neural policy, depth map, or training loop.
The pair illustrates rendered observations at a task pose; a planned path
or occupancy map is not a sensor input.

ONE MECHANISM DETAIL: “Clearance preservation and verification”
Below (a)–(c), draw ONE compact irregular passage cutaway explaining both
generation protection and the subsequent distance check.
Do not repeat two separate robot-and-wall illustrations.

At the near end, show a cross-section with a pale teal protected core and a
smaller robot circle of radius r, surrounded by a dashed safety-margin ring.
The protected core must be visibly larger than r + m because generation
also includes a voxel allowance. Label it “Protected core + voxel allowance”.

Continue this same passage a short distance sideways. Show a magenta dashed
polyline with a few checked sample points inside it. Mark consecutive sample
spacing h and a nearest-wall distance d_min. Keep all points and the polyline
inside the passage. Place this equation beside the detail:
  d_min − h/2 > r + m
One supporting line: “Both meshes · inside + clearance”.
Mark r and m on the robot and margin if needed for clarity.
The formula is a spacing-corrected geometric bound along a checked path,
not a dynamics or policy-execution guarantee.

STYLE
- Charcoal #273444 text, neutral-gray thin arrows.
- Teal #168C9E solid skeleton; pale teal #DDF2F3 protected region.
- Magenta #B64282 dashed independently searched path.
- Muted sandstone #C9B297 rock, with restrained shading.
- Green #397B58 checks; muted red #A65454 failure offshoot.
- Arial/Helvetica-like typography, medium-weight stage titles.
  Titles about 10–11 pt and labels at least 8 pt at final print size.
- Small legend only: “Construction” with a teal solid line, and “Searched path”
  with a magenta dashed line. S/G shapes are clear in the task map.
- Geometry may have subtle depth. Diagrams, text, and connectors stay crisp
  and flat. No glow, glossy gradients, heavy shadows, or stock icons.

EDITORIAL PRIORITIES
Do not add labels simply because space is available. Omit configuration
details, source-audit rules, CAVERS notes, difficulty tiers, output-file lists,
cache details, topology galleries, calibration parameters, and privileged-data
compartments. These belong in the paper text.

All cave miniatures and image thumbnails are method schematics. Do not add
invented results, performance numbers, learned generation, underwater optics,
real-world deployment, or claims of superiority over another method.
Do not turn task S/G markers into claimed physical entrances or exits.

FINAL CHECK
The figure should be understandable in five seconds at column-spanning size.
The largest visual is the generated cave; the second focus is independent
verification. Everything else supports this relationship. If it still feels
busy, simplify geometry detail and remove decoration; never shrink text or
add another panel. Return one clean complete figure.
```

建议 caption（放在论文正文，不绘入图中）：

> **Cave Composer.** Structural conditions define irregular cave geometry with a protected passage. Multiple start–goal tasks are sampled within each cave and independently planned on occupancy. Candidate paths undergo interior and clearance checks against both final visual and collision meshes, with failed requests retained in the records. Accepted tasks support reproducible scene use and paired stereo RGB rendering. The detail illustrates the protected generation region and the spacing-corrected clearance bound along a checked path.

排版检查：缩小至 180 mm 宽时确认文字和公式可读。**Accepted 箭头必须从双网格检查之后出发**；**Occupancy 与 Final meshes 分别进入规划和检查**。双目缩略图仅作为输出示例，不单独占据一个机制面板。
