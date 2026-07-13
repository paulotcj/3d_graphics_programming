# Step 53 — Separate horizontal and vertical FOV

The side frustum planes finally match the screen's real proportions. Until
now one FOV angle built all four side planes — wrong for a non-square
window. Now the vertical FOV stays 60 degrees, and the horizontal FOV is
derived through the aspect ratio:

```
fov_x = atan(tan(fov_y / 2) * aspect_x) * 2
```

`init_frustum_planes(fov_x, fov_y, z_near, z_far)` uses fov_x for the
left/right planes and fov_y for top/bottom — geometry stops popping at the
left/right screen edges.

## What changed vs step 52

- `main.c` `setup()`: computes `aspect_x`/`aspect_y`, `fov_x`/`fov_y`;
  projection uses the vertical pair, the planes use both.
- `clipping.c`: `init_frustum_planes` takes both FOV angles.

## Run it

```
cd PYTHON/53/3d_renderer
py -3.12 main.py
```

Press **H** in the window for the full key list (on-screen help). `ESC`
quits.

## Performance notes

All per-pixel work is vectorized numpy (CONVENTIONS.md §5): barycentric
bounding-box rasterization, masked z-buffer tests, fancy-indexed texture
sampling, batched vertex transforms. Runs at the 60 FPS cap.
