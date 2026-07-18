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

> **Model note:** the real course models are included in this step's
> `assets/` folder and load through the normal OBJ parser, exactly as in the
> C course. If a model file is ever removed, the loader prints a one-line
> warning and falls back to the built-in cube so the step still runs.

## Performance notes

All per-pixel work is vectorized numpy (CONVENTIONS.md §5): barycentric
bounding-box rasterization, masked z-buffer tests, fancy-indexed texture
sampling, batched vertex transforms. Runs at the 60 FPS cap.
