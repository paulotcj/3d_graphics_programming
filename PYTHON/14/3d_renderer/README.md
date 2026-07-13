# Step 14 — No code changes (lecture-only step)

> The C source of step 14 is **byte-identical to step 13** — in the course
> this step is a lecture without code changes. The program below is therefore
> the same perspective point-cloud as step 12; its description is repeated
> here so the folder stands on its own.

The "aha" moment: `project()` now divides x and y by the point's depth — the
similar-triangles rule that makes far things look small:

```
X'/X == 1/Z   →   X' = X/Z     (and Y' = Y/Z)
```

A `camera_position` at z = −5 pushes the cloud away from the viewer (each
point's depth becomes 4..6), and `fov_factor` grows from 128 to 640 to
convert the small X/Z ratios into pixels. The flat square of step 11 becomes
a **cube seen head-on**: the near face projects large, the far face small,
and the layers nest inside each other.

## What changed vs step 11

- `project()`: `fov_factor * point.x` → `(fov_factor * point.x) / point.z`
  (same for y), with the similar-triangles derivation in comments.
- New `camera_position = {0, 0, -5}`; `update()` translates each point away
  from the camera (`point.z -= camera_position.z`) before projecting.
- `fov_factor`: 128 → 640.
- `vector.c`/`vector.h`: comment/whitespace only.

## Run it

```
cd PYTHON/14/3d_renderer
py -3.12 main.py               # 800x600 window
py -3.12 main.py --fullscreen  # borderless desktop-resolution, like the C
```

`ESC` or closing the window quits. You should see nested squares of yellow
dots — a cube in one-point perspective.

## File map

| C file      | Python file  | Notes                              |
|-------------|--------------|-------------------------------------|
| `main.c`    | `main.py`    | game loop + perspective projection |
| `display.c/.h` | `display.py` | window, buffer, drawing helpers |
| `vector.c/.h`  | `vector.py`  | vec2/vec3 types                 |
| `Makefile`  | —            | nothing to compile                 |

## Performance notes

Identical structure to steps 10–11; the 729-point loop mirrors the C and
runs at the 60 FPS cap. All pixel work is vectorized numpy
(CONVENTIONS.md §5).
