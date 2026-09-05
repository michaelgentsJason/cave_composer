# Read-only appearance prior experiment

The requested `/media/hong/Ubun_Shared` is absent in both Windows and WSL.
Searches of Desktop, Downloads and the local download directory did not find the
six named Sketchfab assets. No download authentication was available or bypassed.
No original geometry or material was modified. See `material_inventory.json`.

Local evidence inspected:

- A 228 MB Metashape GLB of a ground-floor scan plus its MTL: four embedded JPEG
  base-color images, metallic factor 0, roughness factor 1, no roughness/normal
  maps. This is consistent with baked photogrammetry atlases, not measured tiled
  rock PBR. It is not a cave-style source and is not transferred.
- CAVERS `rec_handheld_2/RS_COLOR/data/RS_COLOR_0.png`: motion-blurred, noisy and
  strongly illuminated. Rejected as a trustworthy albedo prior.
- Local cave-video frame `v01_s001_f000000_t0000000.jpg`: visible fractured walls,
  ceiling pendants and mineral formations, but colored artificial lights, a person,
  deep shadows and watermark contaminate RGB statistics.

The last image was used only in an explicitly exploratory interface test:
`outputs/material_experiment/reference_fullframe/prior.json`. Quantiles of nonblack,
nonwhite RGB produce a palette, and that palette drives a new periodic procedural
albedo. The original atlas/image is not wrapped onto the generated geometry.
Original pixels are not redistributed as textures. The generator's six default
scenes use hand-defined dry-rock palettes instead.

Result: image-to-palette-to-new-material **works**, but automatic material recovery
is **not validated**. The full-frame palette visibly includes lighting and brown
mineral colors. Roughness remains a declared default; no normal map, physical
roughness, de-lighting, tileable patch recovery or surface-frequency geometry
reconstruction is claimed. The high-frequency statistic is an image-gradient
proxy, not a physical normal/roughness measurement. No water effect is baked by
the default generator. A reference image with water/light tint requires manual
masking and de-lighting before use in production.

Before using actual Sketchfab assets: record creator/license/source and inspect
UVs, exclude seams/padding, select rock-only patches, separate albedo from capture
lighting, and benchmark a held-out patch. If a scan is intended as strict realistic
OOD, learning its appearance prior is leakage and must be a separate experiment.
