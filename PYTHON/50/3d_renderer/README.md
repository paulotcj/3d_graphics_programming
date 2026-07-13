# Step 50 — Polygon clipping data structures

The pipeline gets its clipping seam. After backface culling, each triangle
is wrapped into a `polygon_t` (up to 10 vertices — clipping can add corners)
and run through `clip_polygon()` against all six planes. The per-plane
routine is still a TODO exactly as in the C, so the image is unchanged;
Sutherland-Hodgman fills it in step 51.

## What changed vs step 49

- `clipping.c`: `polygon_t`, `create_polygon_from_triangle()`,
  `clip_polygon()` calling a stubbed `clip_polygon_against_plane()`.
- `main.c`: builds + clips the polygon between culling and projection.

## Run it

```
cd PYTHON/50/3d_renderer
py -3.12 main.py
```

Press **H** in the window for the full key list (on-screen help). `ESC`
quits.

## Performance notes

All per-pixel work is vectorized numpy (CONVENTIONS.md §5): barycentric
bounding-box rasterization, masked z-buffer tests, fancy-indexed texture
sampling, batched vertex transforms. Runs at the 60 FPS cap.
