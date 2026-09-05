# Independent prototype visual review

Before implementing the D/E/F presets or reading PLUME, A/B/C were generated
from the independent field implementation. A: 96,580 triangles, B: 85,428,
C: 64,988. All three were closed and consistently wound in initial checks.

The A/B Blender Cycles interior and cutaway renders revealed:

- Good: continuous walls at prescribed bends, bedding/shelves present, variable
  sections, uneven floor/ceiling, clear geometric difference between A and B.
- Problem: separable sine albedo produced a visible woven/plaid pattern.
  Replaced it with isotropic periodic multiscale Gaussian random fields.
- Problem: exposed formation tops resembled smooth eggs. Changed the obstacle
  field to angular superellipsoids with small fractured relief.
- Remaining: bedding is quite regular, cross sections remain route-biased,
  dense grid limits fine detail. These are realism limits, not navigation proof.

Next: generate branch/chamber/vertical examples, validate both extracted meshes,
and inspect every scene at final render resolution. No scan geometry used.
