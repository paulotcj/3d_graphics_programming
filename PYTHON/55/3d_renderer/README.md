# Step 55 — Encapsulating the display state

A pure refactor, zero visual change: every display global in the C becomes
`static`, reachable only through the new accessor API —
`get_window_width/height()`, `set_render_method()`, `set_cull_method()`,
`is_cull_backface()`, the `should_render_*()` predicates, and
`get/update_zbuffer_at()`. The buffers are allocated by the display module
itself now. The lesson: narrow interfaces beat global variables.

## What changed vs step 54

- `display.c/.h`: all globals static + accessor functions.
- `main.c`/`triangle.c`: use the API instead of the raw globals.
- Python note: the vectorized rasterizer still reads whole buffer slices
  directly (CONVENTIONS.md §5) — the scalar `get/update_zbuffer_at` exist
  for 1:1 API parity and are documented as such.

## Run it

```
cd PYTHON/55/3d_renderer
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
