# Step 46 — Camera and the look-at view matrix

This step introduces a real **camera**: a new `camera` global (position +
direction) and a `mat4_look_at` function that builds a **view matrix** from
the camera position, a target point, and an up vector. Every vertex is now
transformed world space → camera space before projection, so moving the
camera moves the whole scene. The camera drifts up and to the right each
frame while staying locked onto the mesh at (0, 0, 4), so the spinning
textured mesh slides toward the lower-left of the screen.

## What changed vs step 45

Derived from the actual C diff (`45/3d_renderer/src` → `46/3d_renderer/src`):

- **New files `camera.c` / `camera.h`**: a `camera_t` struct (`position`,
  `direction`) and a global `camera` initialized to position (0,0,0),
  direction (0,0,1) → new `camera.py`.
- `matrix.c/.h`: new `mat4_look_at(eye, target, up)` — computes the
  forward/right/up basis (z = normalize(target−eye), x = normalize(up×z),
  y = z×x) and packs it with the −dot(axis, eye) translation column into the
  view matrix.
- `main.c`: new global `view_matrix`; every frame `update()` moves
  `camera.position.x/.y` by +0.008 and rebuilds the view matrix with
  `mat4_look_at(camera.position, {0,0,4}, {0,1,0})`; each vertex is
  multiplied by the view matrix right after the world matrix.
- `main.c`: the old `vec3_t camera_position = {0,0,0}` global was deleted;
  the backface-culling ray now points from vertex A to a local
  `origin = {0,0,0}` — correct because culling now happens in camera space,
  where the camera *is* the origin.
- Minor whitespace-only reformat of the `MAX_TRIANGLES` guard in `main.c`.

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
| `src/matrix.c/.h`       | `matrix.py`   | 4x4 matrices, perspective projection, **mat4_look_at**    |
| `src/camera.c/.h`       | `camera.py`   | **new**: global camera (position + direction)             |
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
- All mesh vertices are transformed by the world matrix and then by the new
  view matrix in **one matmul each per frame** (`vertices @ world_matrix.T @
  view_matrix.T`) instead of C's per-face-per-vertex `mat4_mul_vec4` — a
  documented improvement.

Documented deviations (allowed by §7/§10): windowed 800x600 default with
`--fullscreen` opt-in; the whole event queue is polled per frame (the C code
polls one event, which lags input); missing-asset fallback per §8.
