# Modelling notes

## Iteration workflow

Work in `.work/` until a candidate passes both visual review and rig checks. The
directory is ignored by Git. First establish the complete silhouette, rear hair,
halo and cap attachment; then add face embroidery, clothing and fine seams.
Check each group from the front, three-quarter and back before adding more detail.
Incomplete blockouts can be rendered directly; run the student's full rig checks
once its required components and visibility probes are present.

Existing students can be rebuilt offline. The generators reuse packed references
from the output candidate if it exists, otherwise from the checked-in student
model. Explicit `--reference` and `--character-reference` paths override those
images; both are needed for a student's first build.

```sh
blender --background --factory-startup --python-exit-code 1 --python model_aoba.py -- --output .work/aoba.blend
blender --background .work/aoba.blend --python-exit-code 1 --python test_student_models.py --python render_previews.py -- --preset draft --prefix aoba
```

The draft preset produces 600 × 750 images at 8 samples in `.work/previews/`.
Review silhouettes, missing details and intersections at this stage. For a local
edit, select the affected views and frame the relevant components:

```sh
blender --background .work/aoba.blend --python-exit-code 1 --python render_previews.py -- --preset draft --focus "Cap |" "Halo |" --views three_quarter back --prefix aoba_cap
```

Focus uses the evaluated mesh and curve vertices, since curve bounding boxes can
overestimate their visible size. Surrounding parts remain visible so gaps and
intersections can still be inspected. Rendering restores camera transforms and
render settings on success or failure and never saves the scene.

Once the candidate looks correct, render all three final views once:

```sh
blender --background .work/aoba.blend --python-exit-code 1 --python render_previews.py -- --preset final --prefix aoba_preview --output .work/final
```

The final preset retains 1200 × 1500 and 64 samples. Both presets accept explicit
`--percentage` and `--samples` overrides. Inspect the final images beside the
references, then copy the reviewed candidate and previews to their repository
paths and commit the student's source and assets together. Draft images are not
evidence that fine stitching or final shading is correct.

## Vector sewing patterns

Use a cropped product photo or a same-size black/white part mask to prototype
embroidery, hair cutouts and halo motifs. Trace only the region being worked on:

```sh
uv run --python 3.12 vectorize.py trace reference.jpg .work/eyes.svg --crop 218 452 523 548 --colors 6 --speckle 16
```

`--mask selection.png` selects white pixels and rejects a mismatched canvas.
Crop coordinates are left/top/right/bottom, with right/bottom exclusive. The SVG
retains the full source-image canvas and translates the crop back into place.
Color precision is bits per channel, not a requested number of regions. Inspect
the trace in Inkscape alongside the photograph; remove background, shadow and
fabric-noise paths, merge colors, simplify nodes, and give each part a stable ID.
Keep scleras separate from irises and glints. Hidden contours still need modelling.

Save the reviewed plain-path SVG under `patterns/`, then compile its geometry:

```sh
uv run --python 3.12 vectorize.py prepare patterns/eyes.svg
```

Edit the SVG, not the generated same-name JSON. The compiler resolves viewBox,
nested transforms, cubic/quadratic curves, arcs and basic shapes; it approximates
curves within a sampled pixel tolerance (`--tolerance`, default 0.6). Point budgets
reject excessively dense traces. Convert text, clipping, gradients and effects to
plain opaque paths first; unsupported effects fail rather than disappearing.

Inside Blender, use `sewing_patterns.sew(root, svg_path, depth, materials,
frame=PhotoFrame(...))`. `materials` maps SVG hex colors to Blender materials.
Fills become conforming low-poly panels; evenodd/nonzero compound paths preserve
holes and separate islands. Strokes become round embroidery threads. Paint order
controls relief via `offset` and `layer_gap`; optional integer `data-layer` on a
path/group puts paired left/right pieces at the same depth. Keep the stack shallow.
The importer verifies the source hash and rejects stale JSON. No extra packages
or network are needed inside Blender or for subsequent saved-model builds.

The tracing/compilation script pins [VTracer](https://github.com/visioncortex/vtracer),
Pillow and [svgelements](https://github.com/meerk40t/svgelements). Use Python 3.12:
the pinned VTracer native wheel crashed under the local Python 3.14 interpreter.
To run the vector tests with the same dependencies:

```sh
uv run --python 3.12 --with vtracer==0.6.15 --with Pillow==12.0.0 --with svgelements==1.9.6 python -m unittest test_vectorize
blender --background --factory-startup --python-exit-code 1 --python test_modelling_tools.py
```

Keep large path coordinates in files, not prompts. Review previews and change
component IDs, materials, depths and bone assignments. Token savings and human
modelling-time savings have not been measured.

## Geometry helpers

Use [plush_variants.py](plush_variants.py) to retain the shared body, studio and rig.

- Calibrate a new photo once with `PhotoFrame.fit(center_x=..., floor_y=..., top_y=...)`
  using measured pixel landmarks. Pass that frame to `panel`, `seam` and `oval`.
  The default model height is 3.4 Blender units, or 170 mm at this repository's
  scale. `PhotoFrame()` preserves the existing Nozomi/Aoba coordinate mapping.
- `surface(obj)` snapshots the evaluated geometry and rejects projection misses
  with the component name and model coordinates. Create a new snapshot after
  changing the target. Use `fallback='nearest'` only for deliberate extrapolation;
  the existing student scripts retain this explicitly for compatibility.
- For a curved patch, start with a coarse spacing and add `tolerance=.003` to
  `panel`. It refines where edge midpoints or triangle centroids deviate from the
  target surface. Flat regions stay sparse, concave cutouts remain open, and an
  exceeded `max_vertices` budget or non-converging depth field raises an error
  before linking the new piece. The default adaptive budget is 4,096 vertices.
- Tolerance measures sampled **base-mesh** depth error, before Subdivision and
  Solidify. It is not a collision guarantee: inspect the evaluated result, including
  cuffs, cap/brim joins and layered embroidery. Reduce error before increasing
  the offset; a large offset can leave a patch visibly floating.
- Attach pieces after setting their transforms. If a control's rest position
  changes, preserve and restore its children's world matrices. Test both movement
  and reset, including attached halos and hair pieces.

Run the helper tests with:

```sh
blender --background --factory-startup --python-exit-code 1 --python test_modelling_tools.py
```

For a new student, add its visibility probes and control expectations to
`test_student_models.py`, converting probe coordinates with the same `PhotoFrame`.

For workflow changes that should preserve an existing model, compare the saved
candidate's evaluated geometry, topology, bindings, rest bones, palette and packed
references, then run its rig tests:

```sh
blender --background --factory-startup --python-exit-code 1 --python test_rebuild.py -- --baseline aoba_chocopuni.blend --candidate .work/aoba.blend
```

## Measured review cost

| Case | Before | After | Change |
| --- | ---: | ---: | ---: |
| [Aoba front render](render_previews.py), final → draft | 47.845 s | 4.332 s | 90.9% less wall time; 11.0× |
| [Curved patch](test_modelling_tools.py), uniform → adaptive: vertices | 965 | 409 | 57.6% fewer |
| [Curved patch](test_modelling_tools.py), maximum probed depth error | 0.091894 | 0.002981 | 96.8% less |

The render comparison is one run per preset in Blender 5.2.1, Cycles CPU with eight
threads, using the same `aoba_chocopuni.blend` and `Front comparison` camera. Wall
time includes Blender startup; use `time blender --background aoba_chocopuni.blend
--threads 8 --python render_previews.py -- --preset draft --views front` to repeat
the draft measurement. The reduction comes from lower review resolution and sample
count; final output retains the original settings. Human modelling time was not measured.

The synthetic patch is 0.8 × 0.8 units on a unit sphere, rerun after direct triangle
refinement was added for SVG patterns. Uniform spacing is `.025`;
adaptive starts at `step=1` with `tolerance=.003`. Independent barycentric probes
measure the final depth error. Uniform interior sampling leaves long boundary
edges, which explains its larger error despite the higher vertex count.
Adaptive refinement shares new edge midpoints between neighboring triangles;
rerunning constrained Delaunay can discard collinear boundary samples. This
preserves holes and avoids T-junctions without relying on repeated retriangulation.

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

Use the [iteration workflow](#iteration-workflow) for previews and validation.
Compare final renders beside the product photo at the same scale. A base vertex
count alone does not validate silhouettes, panel intersections, a complete halo,
or attachment to the rig.
