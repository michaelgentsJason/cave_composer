# Stonefish interface: PARTIAL

The adapter emits a candidate `.scn` for the Stonefish 1.6 documentation, with
separate physical and visual OBJ paths. Static models support concave collision;
we explicitly set `convex=false`. A convex hull would fill a cave's navigable
interior, so use spatial wall patches if concave collision becomes too expensive.
[Official static-body documentation](https://stonefish.readthedocs.io/en/latest/environment.html#static-bodies)

OBJ MTL definitions are not consumed by Stonefish. The adapter supplies a named
look with an explicit albedo PNG; roughness is a scalar. Blender's shader bump is
not silently claimed as simulator detail. Normals into the void are appropriate
for interior visual surfaces; actual one/two-sided collision behavior still needs
a runtime test. [Geometry requirements](https://stonefish.readthedocs.io/en/latest/scenario.html#preparing-geometry-files),
[looks](https://stonefish.readthedocs.io/en/latest/materials.html#looks)

Composer coordinates are right-handed Z-up. The scene applies a rotation of pi
around X followed by a +20 m NED-depth translation, also applied to spawn and goal:
`(x,y,z) -> (x,-y,20-z)`. Its determinant is +1, preserving winding and distances.
Set the simulator data directory to the bundle root; paths are portable relative
paths. [Frame guidance](https://stonefish.readthedocs.io/en/latest/scenario.html#what-is-a-good-quality-mesh)

The generated scene defines water separately from the rock. Change the ocean
parameters without touching cave geometry/albedo. It contains no robot, camera,
or task controller. The export uses the element/attribute organization checked
against the official parser's `ParseStatic` and `ParseLooks` implementations.
[Parser source](https://github.com/patrykcieslak/stonefish/blob/master/Library/src/core/ScenarioParser.cpp)

```bash
python scripts/export_stonefish.py outputs/final/cave_b_sharp_turns --depth 20
```

Checked here: XML well-formedness, referenced file existence, relative path
resolution, positive underwater depth, rigid-coordinate transformation, scale
and mesh/pose agreement. **Not executed:** Stonefish parser or simulation. This
is an interface prototype, not a claim of end-to-end simulator readiness.

Next integration gate: load one static cave, place a sphere/robot at the supplied
spawn, raycast toward each wall, verify collision from inside, attach a camera and
spotlight, traverse the validated path, then benchmark several independent
instances. Do not conflate Blender background rendering with a fully graphical
Stonefish sensor simulation; console mode lacks camera rendering.
[Simulator modes](https://stonefish.readthedocs.io/en/latest/building.html)
