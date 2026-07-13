# Step 43 — A real textured OBJ model (crab)

The payoff step: `setup()` loads `crab.obj` with `crab.png` and the default
render mode becomes **textured** — mesh loading, UV parsing,
perspective-correct sampling and the painter's sort all working together.

## What changed vs step 42

- `main.c`: crab.obj/crab.png; default mode `RENDER_TEXTURED`; y-rotation
  0.004/frame.
- `texture.c` texel lookup gains a `% texture_size` wrap (this conversion
  already wrapped — noted in triangle.py).

## Run it

```
cd PYTHON/43/3d_renderer
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
