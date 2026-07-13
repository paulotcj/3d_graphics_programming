# Step 44 — Z-buffer for per-pixel depth testing

A second full-screen buffer stores each pixel's depth as **adjusted 1/w**
(`1.0 - 1/w`, so smaller = closer). A textured pixel is drawn only if it is
closer than what the buffer already holds. Depth is resolved *per pixel*
instead of per triangle — fixing every case the painter's algorithm gets
wrong. The sort is kept only for the filled render modes.

## What changed vs step 43

- `display.c`: `z_buffer` allocation + `clear_z_buffer()` (reset to 1.0).
- `triangle.c` textured path: `if (1 - 1/w) < z_buffer[pixel]` → draw and
  store. In numpy this is one boolean mask + two fancy-indexed stores.
- `main.c`: f117.obj/f117.png, x-rotation 0.006, z = 4; painter's sort only
  for `RENDER_FILL_TRIANGLE*` modes; render() clears the z-buffer.

## Run it

```
cd PYTHON/44/3d_renderer
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
