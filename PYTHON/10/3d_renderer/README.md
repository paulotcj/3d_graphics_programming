# Step 10 — Vectors and a 3D point cloud cube

The first 3D data in the program. A new `vector.py` (mirroring `vector.h`'s
`vec2_t`/`vec3_t`) defines the vector types, and `main.py` builds a **9×9×9
cloud of 729 points** filling the cube from −1 to 1 on each axis. Every frame
each point is run through `project()` — which at this step just drops the z
coordinate — and drawn as a 4×4 yellow square offset to the screen center.

Don't expect much on screen yet: the raw coordinates only span −1..1 and
nothing scales them up, so all 729 squares overlap in a **tiny yellow blob**
at the center — identical to what the C step shows. Step 11 adds the
`fov_factor` scaling that spreads the cloud out.

## What changed vs step 9

- New `vector.c`/`vector.h` → [vector.py](vector.py): `vec2_t`, `vec3_t`
  (numpy-array based here, with `vec2_new`/`vec3_new` constructors).
- `display.c` gained `draw_pixel(x, y, color)` with a bounds check;
  `draw_rect` now writes through it → mirrored in [display.py](display.py)
  (the slice clamp is the same check applied to the whole rect at once).
- `main.c`: `cube_points`/`projected_points` arrays, `fov_factor = 128`
  (unused until step 11), `project()`, point projection in `update()`, and
  per-point rectangles in `render()` (color `0xFFFFFF00`).

## Run it

```
cd PYTHON/10/3d_renderer
py -3.12 main.py               # 800x600 window
py -3.12 main.py --fullscreen  # borderless desktop-resolution, like the C
```

`ESC` or closing the window quits.

## File map

| C file      | Python file  | Notes                                 |
|-------------|--------------|----------------------------------------|
| `main.c`    | `main.py`    | game loop + point cloud + projection  |
| `display.c/.h` | `display.py` | window, buffer, drawing helpers    |
| `vector.c/.h`  | `vector.py`  | vec2/vec3 types (math comes later) |
| `Makefile`  | —            | nothing to compile                    |

## Performance notes

729 points is tiny; the per-point Python loop mirrors the C exactly and still
renders at the 60 FPS cap. The heavy operations (grid, rect fills, clear,
present) are the vectorized numpy routines in `display.py`
(CONVENTIONS.md §5).
