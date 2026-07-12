# Step 34 — Perspective projection matrix

This step replaces the naive fov-factor projection (`x*640/z`) with a real
**perspective projection matrix**: `mat4_make_perspective` builds a matrix
from the field of view (60°), the window aspect ratio, and near/far planes,
and `mat4_mul_vec4_project` applies it and performs the perspective divide
by w. Projected points land in normalized device coordinates and are scaled
to half the screen size, then centered. The cube rotates only around x so
the new projection is easy to inspect.

## What changed vs step 33

Derived from the actual C diff (`33/3d_renderer/src` → `34/3d_renderer/src`):

- `matrix.c/h`: new `mat4_make_perspective(fov, aspect, znear, zfar)` — the
  classic perspective matrix; its last row copies camera-space z into w.
- `matrix.c/h`: new `mat4_mul_vec4_project(mat_proj, v)` — multiplies by the
  projection matrix, then divides x, y, z by w (when w ≠ 0).
- `main.c`: global `fov_factor = 640` and the `project()` function are
  **removed**; a global `mat4_t proj_matrix` is added.
- `main.c` `setup()`: initializes `proj_matrix` with fov = π/3 (60°),
  aspect = window_height / window_width, znear = 0.1, zfar = 100.0.
- `main.c` `update()`: `projected_points` become `vec4_t`; each vertex is
  projected with `mat4_mul_vec4_project`, **scaled into the view**
  (× width/2, × height/2 — new) and then translated to the screen center.
- `main.c` `update()`: only `mesh.rotation.x += 0.01` animates now
  (rotation y and z are commented out).
- Cosmetic: tabs-to-spaces cleanups in `main.c`/`matrix.c`.

## Run it

```
pip install pygame numpy
python main.py               # 800x600 window (add --fullscreen for the C behavior)
```

| Key | Action                              |
|-----|-------------------------------------|
| 1   | Wireframe + red vertex dots         |
| 2   | Wireframe only                      |
| 3   | Filled triangles                    |
| 4   | Filled triangles + wireframe        |
| c   | Enable back-face culling            |
| d   | Disable back-face culling           |
| ESC | Quit                                |

Test hooks: `RENDERER_MAX_FRAMES=<n>` exits after n frames;
`RENDERER_SAVE_FRAME=<path.png>` saves the last frame; works under
`SDL_VIDEODRIVER=dummy`.

## File map

| C file              | Python file   | Notes                                            |
|---------------------|---------------|--------------------------------------------------|
| `src/main.c`        | `main.py`     | game loop, pipeline, painter's-algorithm sort    |
| `src/display.c/h`   | `display.py`  | window, color buffer, grid/pixel/line/rect       |
| `src/vector.c/h`    | `vector.py`   | vec2/vec3/vec4 helpers                           |
| `src/matrix.c/h`    | `matrix.py`   | mat4 constructors + `mat4_make_perspective`/`mat4_mul_vec4_project` |
| `src/mesh.c/h`      | `mesh.py`     | cube data, OBJ loader, mesh transform state      |
| `src/triangle.c/h`  | `triangle.py` | `face_t`/`triangle_t`, wire + filled rasterizers |
| `src/array.c/h`     | not ported    | C dynamic array → Python `list`                  |
| `int_swap` (triangle.c) | not ported | tuple swap `a, b = b, a`; the barycentric fill needs no sorting |

`setup()` loads the hard-coded cube (the OBJ call is commented out, exactly
like the C code). `assets/cube.obj` is provided anyway so the parser can be
exercised; drop the original course `.obj` files into `assets/` to load real
models (missing files fall back to the built-in cube with a warning — the C
code would crash on the NULL `FILE*`).

## Performance notes

NumPy tricks used this step (CONVENTIONS.md §5):

- `clear_color_buffer` / `draw_grid`: full-buffer and strided-slice
  assignments (`buffer[::10, ::10] = color`).
- `draw_rect`: one clipped 2-D slice assignment.
- `draw_line`: DDA vectorized with `np.linspace` + one fancy-indexed store.
- `draw_filled_triangle`: the C flat-top/flat-bottom scanline fill is
  re-expressed as a **barycentric bounding-box rasterizer** — all pixels in
  the triangle's bounding box are tested and stored in one array operation.
- All mesh vertices are transformed in **one matmul per frame**
  (`homogeneous @ world_matrix.T`); the C code rebuilds the identical world
  matrix and multiplies vertex-by-vertex inside the face loop. The world
  matrix is composed with the same `mat4_mul_mat4` order as the C code.
- Triangle depth sort uses Python's built-in `sort` (O(n log n)) instead of
  the C O(n²) swap sort — same descending order.

Documented deviations: windowed 800x600 default (§7), whole-event-queue
polling instead of the C single `SDL_PollEvent` (§10), and OBJ-loaded faces
default to white instead of the C code's zero-initialized (black) face color.
