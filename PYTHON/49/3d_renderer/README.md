# Step 49 — Frustum planes for clipping

Scaffolding for clipping: a new `clipping.py` (mirroring `clipping.c`)
defines the six **frustum planes** — near, far, and four side planes tilted
half the FOV outward, each stored as a point + inward normal built from
sin/cos of fov/2. Nothing is clipped yet; steps 50-52 use these planes.

## What changed vs step 48

- New `clipping.c`/`clipping.h` → [clipping.py](clipping.py):
  `init_frustum_planes(fov, z_near, z_far)` + the plane enum.
- `setup()` initializes the planes next to the projection matrix; default
  render mode back to wireframe; scene: cube.obj/cube.png.

## Run it

```
cd PYTHON/49/3d_renderer
py -3.12 main.py
```

Press **H** in the window for the full key list (on-screen help). `ESC`
quits.

## Performance notes

All per-pixel work is vectorized numpy (CONVENTIONS.md §5): barycentric
bounding-box rasterization, masked z-buffer tests, fancy-indexed texture
sampling, batched vertex transforms. Runs at the 60 FPS cap.
