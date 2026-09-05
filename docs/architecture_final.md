# Final v0 architecture decision

Keep the independent constraint-first implicit architecture. The PLUME source
review confirms that volume operations are not a novelty claim; the contribution
candidate is the robotics contract around generation: exact task syntax, separately
validated meshes, reproducible split distributions, semantic GT and geometric
look-ahead. See `plume_comparison.md` for evidence and adoption decisions.

The v0 construction samples a local nearest-segment field on a regular grid. The
KD candidate approximation can change across space, so the implemented globally
continuous object is the **interpolated sampled lattice**, not a certified analytic
SDF. The field magnitude is never used as a distance certificate. Mesh-to-polyline
distance and inside tests independently establish the navigation witness.

Changes from the initial design, justified by observed failures:

1. Remove small isolated void components before extraction, recording voxel counts;
   reject if discarded volume would exceed 1%. Clamp near-zero lattice values to
   avoid tiny triangles. The source field and both grids stay deterministic.
2. Reserve `safety_radius + 2.1*collision_voxel` and reject requested dimensions
   incompatible with that discretization. All final A–F have continuous-polyline
   mesh-clearance lower bounds above the requested 0.55 m safety radius.
3. Treat Euler values as diagnostics. Local rock handles are not semantic route
   loops. Detect sampled robot-clear connections between graph-distant route nodes;
   exact recovery of all navigable topology remains unimplemented.
4. Add an independent Blender triangle-overlap audit. A–F have zero detected
   nonadjacent intersecting pairs. This is floating-point evidence, not exact
   computational-geometry proof.
5. Export packed editable Blender scenes, periodic standalone albedo and explicit
   Stonefish look/pose candidates. Material appearance priors from selected CAVERS
   rock regions affect only a separate appearance experiment.

Future substitutions that preserve the contract: sparse field bricks, adaptive
collision meshing with post-validation, learned or fitted geological morphology,
chunked PBR material baking, full recovered-topology comparison, dynamic formation
objects and simulator-specific parallel scheduling. None is claimed implemented.
