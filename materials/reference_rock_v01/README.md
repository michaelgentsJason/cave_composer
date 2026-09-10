# Reviewed reference rock patches

Four appearance patches derived from captured-color atlases by **cave-dive-make**
([author](https://sketchfab.com/cave-dive-make)), with embedded source metadata
identifying **CC BY 4.0** ([license](https://creativecommons.org/licenses/by/4.0/)).

- `font_del_truffe_small_part_of_sump_2_patch_06`: [Font del Truffe, small part of Sump 2](https://sketchfab.com/3d-models/font-del-truffe-small-part-of-sump-2-b15476c708f7424ba77b0cd0a4c411e0).
- `porth_yr_ogof_-_sump_9_patch_03` and `patch_05`: [Porth Yr Ogof - Sump 9](https://sketchfab.com/3d-models/porth-yr-ogof-sump-9-3cf9f626271f47c2be9dc7e7ad1ecf9e).
- `porth_yr_ogof_-_upper_cave_water_chamber_patch_04`: [Porth Yr Ogof - Upper Cave Water Chamber](https://sketchfab.com/3d-models/porth-yr-ogof-upper-cave-water-chamber-10056f5a22c6477db660e58b2a7c526f).

Changes: select rock-only atlas regions using UV coverage and visual review,
crop, remove the smooth boundary-discontinuity component, clip to RGB, save PNG.
`*_repeat.png` previews repeat the resulting patch 2 × 2. Generation optionally
rotates a patch by multiples of 90 degrees, projects it on new geometry, and
bakes it into UV textures. No scanned geometry is included in these PNG files.

`library.json` retains exact crop coordinates, hashes, source links, credits,
native pixel dimensions, and transformations for each entry. These captured
appearance patches can retain lighting; they are not measured PBR materials.
Source groups are development priors, not untouched test data.

See [integration and example](../../docs/reference_texture_pipeline_v01.md).
