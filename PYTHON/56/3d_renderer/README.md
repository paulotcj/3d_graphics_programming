# Step 56 — Encapsulating the global light

The twin of step 55, applied to `light.c`: the light global becomes static,
set once via `init_light(direction)` in `setup()` and read via
`get_light_direction()` in the shading code.

## What changed vs step 55

- `light.c/.h`: static global + `init_light` / `get_light_direction`.
- `main.c`: calls `init_light(vec3_new(0, 0, 1))`; shading reads the getter;
  mesh spins +0.5 rad/s on x at z = 5.

## Run it

```
cd PYTHON/56/3d_renderer
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
