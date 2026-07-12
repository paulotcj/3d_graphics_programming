# Step 33 — World matrix (mat4_mul_mat4)

This step finishes the move to matrix-based transformations: instead of
multiplying every vertex by five separate matrices, a single **world matrix**
is composed once with the new `mat4_mul_mat4` — scale first, then the three
rotations, then translation (`[T]*[R]*[S]*v`). With all three rotation axes
animating again, the cube tumbles freely while being back-face culled,
depth-sorted (painter's algorithm), and drawn as wireframe or flat-filled
triangles.

## What changed vs step 32

Derived from the actual C diff (`32/3d_renderer/src` → `33/3d_renderer/src`):

- `matrix.c/h`: new `mat4_mul_mat4(a, b)` — full 4x4 x 4x4 matrix product.
- `main.c` `update()`: the per-vertex chain of five `mat4_mul_vec4` calls is
  replaced by composing a single `world_matrix` (`mat4_identity`, then
  `mat4_mul_mat4` with scale, rotation z, rotation y, rotation x,
  translation) and one `mat4_mul_vec4(world_matrix, vertex)` per vertex.
- `main.c` `update()`: `mesh.rotation.x += 0.01` and `mesh.rotation.z += 0.01`
  are re-enabled (step 32 only animated rotation y), so the cube now rotates
  around all three axes; `mesh.translation.z = 5.0` stays.
- Cosmetic: `camera_position` initializer style and tabs-to-spaces cleanups.

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
| `src/matrix.c/h`    | `matrix.py`   | mat4 constructors + `mat4_mul_vec4`/`mat4_mul_mat4` |
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
