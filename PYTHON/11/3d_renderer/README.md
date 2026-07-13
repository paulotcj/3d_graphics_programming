# Step 11 — Orthographic projection with FOV scaling

One-line change with a big visual payoff: `project()` now multiplies x and y
by `fov_factor` (128), so the −1..1 point-cloud coordinates from step 10
spread across the screen. You now see a **filled square of yellow 4×4
rectangles** — a flat, *orthographic* view of the 9×9×9 cube: points at every
depth land on the same screen spot, so the cloud still looks 2D. Perspective
arrives in step 12.

## What changed vs step 10

- `project()`: `.x = point.x` → `.x = fov_factor * point.x` (same for y).
- Everything else is comment/whitespace cleanup.

## Run it

```
cd PYTHON/11/3d_renderer
py -3.12 main.py               # 800x600 window
py -3.12 main.py --fullscreen  # borderless desktop-resolution, like the C
```

`ESC` or closing the window quits.

## File map

| C file      | Python file  | Notes                              |
|-------------|--------------|-------------------------------------|
| `main.c`    | `main.py`    | game loop + projection             |
| `display.c/.h` | `display.py` | window, buffer, drawing helpers |
| `vector.c/.h`  | `vector.py`  | vec2/vec3 types                 |
| `Makefile`  | —            | nothing to compile                 |

## Performance notes

Identical to step 10: the 729-point loop mirrors the C; all pixel work is
vectorized numpy (CONVENTIONS.md §5). Runs at the 60 FPS cap.
