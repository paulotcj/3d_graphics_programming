# Step 48 — Keyboard-controlled FPS camera

The camera answers to the keyboard. The automatic drift is gone — arrows
move the camera up/down, `a`/`d` turn (yaw), `w`/`s` move along the current
viewing direction, everything scaled by delta_time. The look-at target is
rebuilt from the yaw angle every frame: rotate (0,0,1) by the yaw matrix,
offset by the camera position.

## What changed vs step 47

- `camera.h`: `forward_velocity` and `yaw` fields.
- `main.c` input: UP/DOWN move y; a/d change yaw; w/s move along
  `camera.direction`; culling toggles move to `c` (on) / `x` (off) since
  `d` now steers.
- View target computed from yaw; scene: efa.obj/efa.png, frustum tightened
  (znear 1.0, zfar 20.0), no mesh self-rotation.

## Run it

```
cd PYTHON/48/3d_renderer
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
