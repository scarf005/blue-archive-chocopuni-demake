# Modelling notes

## Hikari v4 geometry reduction

The earlier “about 100,000 to 7,000 vertices” estimate should be read as a rough
description. Measuring the committed files gives **70,058 to 7,000 base mesh
vertices**, including the four-vertex studio floor. The student alone has 6,996.
These are editable mesh vertices, not the final geometry after modifiers and curves.

Measured in Blender 5.2.1, using the active scene at its saved neutral pose:

| Metric | [v3](https://github.com/scarf005/blue-archive-chocopuni-demake/tree/4ebf76a2637015979827d92532664738f42df87b) | [v4](https://github.com/scarf005/blue-archive-chocopuni-demake/tree/6e11f322a95d01db18c0462df92bc41da3fcf557) | Reduction |
| --- | ---: | ---: | ---: |
| Base mesh vertices | 70,058 | 7,000 | 90.0% |
| Evaluated mesh vertices | 87,846 | 30,766 | 65.0% |
| Evaluated mesh + curve vertices | 220,014 | 162,934 | 25.9% |
| Compressed `.blend` bytes | 2,071,088 | 715,280 | 65.5% |

Run `blender --background <model.blend> --python model_stats.py` to report the same
geometry counts. These measurements describe the historical v3/v4 files, before
the rig and complete halo were added. No runtime or render-time speedup was measured.

The v4 workflow applied Collapse Decimate to each mesh **before** its existing
Solidify modifier. It left meshes with at most 50 vertices alone and disabled
`use_collapse_triangulate`. The final allocation used these ratios:

| Part | Collapse ratio |
| --- | ---: |
| Hair | 0.1475 |
| Face cushion | 0.0835 |
| Crown and visor | 0.04 |
| Other face embroidery | 0.10 |
| Other cap panels | 0.08 |
| Uniform | 0.025 |
| Shoes | 0.03 |
| Other meshes | 0.04 |

The ratios control decimation, not an exact vertex percentage. Hair retained 4,411
base vertices because its cut edges and curls need more detail than the body.
The face cushion, all hair meshes, crown, and visor then received Catmull–Clark
Subdivision at **one viewport and one render level**, with `PRESERVE_CORNERS`.
Subdivision precedes Solidify so the thin hair panels keep their cloth thickness.
Flat embroidery, straps, and small trim did not receive Subdivision.

Dense individual fabric-pile curves had already been removed in v3. Procedural
fabric bump, weave, and sheen still provide the cloth surface. Satin-stitch and seam
curves remained; their evaluated vertices are why the final scene is larger than
the 7,000-vertex base mesh budget. Removing unused scenes and orphaned data and
saving with compression reduced storage separately from geometry.

For new students, start with sparse stuffed forms and shallow conforming felt
panels. Spend vertices on hair silhouettes and facial readability; use the v4
allocation as a guide, not a requirement to hit exactly 7,000. Keep reference photos,
materials, editable curves, and pose controls. Do not apply a blanket decimation
ratio to an already weighted rig.

## References and inspection

- [Official Chocopuni product photos](https://www.goodsmile.com/en/product/1140953/Chocopuni+Plushie+Aoba+Hikari+Nozomi)
  establish the seated proportions, approximately 170 mm height, and fabric details.
- [Hikari cap photograph, image 2](https://arca.live/b/bluearchive/181993371)
  shows the continuous white felt backing, green concentric motif, and side wings.
  The halo belongs behind the crown and follows the head control.
- Inspect student rear/side art for details obscured in front product photos;
  retain explicit model notes for details that the available views do not show.

Render saved files with `blender --background <model.blend> --python render_previews.py`.
Use `-- --prefix <student>_preview` for a new student's front, three-quarter, and
back WebP previews. Inspect them beside the product photo at the same scale, then
test head/limb movement and reset. A base vertex count alone does not validate
silhouettes, panel intersections, a complete halo, or attachment to the rig.
