# Step 35 — Flat shading with a directional light

The scene gets its first light. A new `light.py` (mirroring `light.c`) owns a
single **directional light** and `light_apply_intensity()`, which darkens a
`0xAARRGGBB` color channel-by-channel with the C bit-mask trick. Shading is
**flat**: one brightness per face — `-dot(face_normal, light.direction)` —
the negation because a face whose normal points *against* the incoming rays
is the lit one.

## What changed vs step 34

- New `light.c`/`light.h` → [light.py](light.py).
- The face normal is computed **unconditionally** now (culling only tests
  it; lighting uses it) and is normalized (intensity needs unit length).
- Projected `y *= -1` — 3D y grows up, screen y grows down (a real course
  bug fix; models were upside-down until now).
- Default render mode: filled; mesh f22.obj (cube fallback); rotation 0.005.
- All cube face colors change from rainbow to white (shading is the point).

## Run it

```
cd PYTHON/35/3d_renderer
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
