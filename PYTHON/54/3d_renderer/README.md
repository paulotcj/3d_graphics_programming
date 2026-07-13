# Step 54 — Texture coordinates survive clipping

UVs travel through the clipper. When Sutherland-Hodgman splits an edge at a
frustum plane, the same interpolation factor `t` that places the new vertex
also lerps the texture coordinates (`float_lerp`), and the triangles rebuilt
from the polygon carry those clipped UVs to the rasterizer. Until now a
clipped textured triangle kept its ORIGINAL corner UVs — visibly wrong
mapping at the screen edges.

## What changed vs step 53

- `clipping.c`: `polygon_t` gains `texcoords[]`; `polygon_from_triangle`
  takes the three UVs; the clip loop lerps UVs with the same `t`; new
  `float_lerp`; `triangles_from_polygon` copies UVs out.
- `texture.c`: `tex2_clone`. `main.c`: passes face UVs into the polygon and
  reads them back from each clipped triangle.

## Run it

```
cd PYTHON/54/3d_renderer
py -3.12 main.py
```

Press **H** in the window for the full key list (on-screen help). `ESC`
quits.

> **Model note:** the original course `.obj` models were never committed to
> this repository, so this mirror ships **generated stand-in models** (low-poly
> but recognizable — see `# comments` inside each `.obj`). They load through
> the very same parser path the course teaches. If you have the original
> course models, drop them into `assets/` and they replace the stand-ins
> as-is; if a model file is missing entirely, the loader still falls back to
> the built-in cube with a console warning.

## Performance notes

All per-pixel work is vectorized numpy (CONVENTIONS.md §5): barycentric
bounding-box rasterization, masked z-buffer tests, fancy-indexed texture
sampling, batched vertex transforms. Runs at the 60 FPS cap.
