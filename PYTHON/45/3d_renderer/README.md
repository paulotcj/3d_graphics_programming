# Step 45 — Z-buffer everywhere (goodbye painter's algorithm)

This step completes the move from sorting triangles to per-pixel depth
testing: the **filled** (flat-shaded) triangle path now uses the z-buffer
too, exactly like the textured path did since the previous step. With
visibility resolved per pixel, the painter's-algorithm depth sort is deleted
for good, and the frame's triangles live in a fixed-capacity array instead
of a growable one. The scene is a single spinning textured mesh (the course
loads `efa.obj` with `efa.png`).

## What changed vs step 44

Derived from the actual C diff (`44/3d_renderer/src` → `45/3d_renderer/src`):

- `triangle.c`: `draw_filled_triangle` was rewritten — it now takes
  `(x, y, z, w)` per vertex and fills scanlines through a new
  `draw_triangle_pixel` helper that interpolates `1/w` with barycentric
  weights and depth-tests each pixel against the z-buffer (the same
  structure the textured path uses). The old `fill_flat_bottom_triangle` /
  `fill_flat_top_triangle` helpers were removed, and `draw_texel` was
  renamed `draw_triangle_texel`.
- `main.c`: the painter's-algorithm bubble sort by `avg_depth` was deleted,
  and `avg_depth` was removed from `triangle_t` (`triangle.h`).
- `main.c`: `triangles_to_render` changed from an `array.c` dynamic array to
  a fixed `triangle_t[MAX_TRIANGLES]` (10000) with a
  `num_triangles_to_render` counter, so the per-frame `array_push` /
  `array_free` churn is gone.
- `main.c`: `world_matrix` was promoted from a local in `update()` to a
  global next to `proj_matrix`; the render loop passes `z`/`w` through to
  `draw_filled_triangle`; `fov` uses the literal `3.141592 / 3.0` instead of
  `M_PI / 3.0`; the scene mesh changed from `f117.obj`/`f117.png` to
  `efa.obj`/`efa.png`.
- Whitespace/comment cleanups in `display.c`, `light.c`, `matrix.c`,
  `mesh.c`, `swap.c`, `texture.c`, `vector.c` (no behavior change).

## Run it

```sh
pip install pygame numpy
python main.py               # 800x600 window (default)
python main.py --fullscreen  # borderless desktop-resolution window, like the C code
```

| Key   | Action                                        |
|-------|-----------------------------------------------|
| `ESC` | Quit                                          |
| `1`   | Wireframe + red vertex dots                   |
| `2`   | Wireframe only                                |
| `3`   | Filled flat-shaded triangles (z-buffered)     |
| `4`   | Filled + wireframe                            |
| `5`   | Textured (default)                            |
| `6`   | Textured + wireframe                          |
| `c`   | Enable backface culling (default)             |
| `d`   | Disable backface culling                      |

Test hooks (CONVENTIONS.md §7): `RENDERER_MAX_FRAMES=<n>` exits after n
frames; `RENDERER_SAVE_FRAME=<path.png>` saves the final frame;
`SDL_VIDEODRIVER=dummy` runs headless.

**Missing models (§8):** the course repository never committed the `.obj`
files, so `efa.obj` is not present. `load_obj_file_data` warns and falls
back to the built-in cube (parsing the generated `assets/cube.obj` so the
OBJ parser is still exercised) while keeping `efa.png` as the texture. Drop
the original course `efa.obj` into `assets/` to see the real model.

## File map

| C file                  | Python file   | Notes                                                     |
|-------------------------|---------------|-----------------------------------------------------------|
| `src/main.c`            | `main.py`     | game loop, pipeline, controls, test hooks                 |
| `src/display.c/.h`      | `display.py`  | window, color/z buffers, grid/pixel/line/rect, mode flags |
| `src/vector.c/.h`       | `vector.py`   | vec2/vec3/vec4 math                                       |
| `src/matrix.c/.h`       | `matrix.py`   | 4x4 matrices, perspective projection                      |
| `src/light.c/.h`        | `light.py`    | global directional light + intensity helper               |
| `src/triangle.c/.h`     | `triangle.py` | face/triangle types, wire/filled/textured rasterizers     |
| `src/texture.c/.h`      | `texture.py`  | `tex2_t` + global mesh texture                            |
| `src/mesh.c/.h`         | `mesh.py`     | global mesh, cube data, OBJ loader                        |
| `src/upng.c/.h`         | not ported    | replaced by `pygame.image.load` in `texture.py`           |
| `src/array.c/.h`        | not ported    | C dynamic arrays become Python lists                      |
| `src/swap.c/.h`         | not ported    | tuple swap `a, b = b, a` (unused after vectorization)     |

## Performance notes

NumPy tricks used in this step (CONVENTIONS.md §5):

- `clear_color_buffer` / `clear_z_buffer`: single broadcast assignments.
- `draw_grid`: strided slice `color_buffer[::10, ::10]`.
- `draw_rect`: clipped 2-D slice assignment.
- `draw_line` (DDA): `np.linspace` both axes, round, mask, one fancy-indexed
  store.
- Filled **and** textured triangles: the barycentric bounding-box rasterizer
  — the C scanline loops (`draw_triangle_pixel` / `draw_triangle_texel` per
  pixel) become array math over the triangle's bounding box, with the
  z-test done as a boolean mask against a z-buffer slice and the texture
  sampled via fancy indexing.
- All mesh vertices are transformed by the world matrix in **one matmul per
  frame** (`mesh_homogeneous_vertices @ world_matrix.T`) instead of C's
  per-face-per-vertex `mat4_mul_vec4` — a documented improvement.

Documented deviations (allowed by §7/§10): windowed 800x600 default with
`--fullscreen` opt-in; the whole event queue is polled per frame (the C code
polls one event, which lags input); missing-asset fallback per §8.
