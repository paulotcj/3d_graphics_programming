# Step 57 — Multiple meshes

This step turns the renderer into a real *scene* renderer: instead of one
global mesh with one global texture, the program keeps a static array of
meshes, each loaded with `load_mesh(obj, png, scale, translation, rotation)`
and carrying its **own texture**. `setup()` places two airplanes (f22 and
efa) side by side, and the update loop runs the whole graphics pipeline once
per mesh. The camera also gained a pitch angle, driven from the keyboard
through a new getter/setter API.

## What changed vs step 56

Derived from the actual C diff (`56/3d_renderer/src` → `57/3d_renderer/src`):

- **mesh.c — multiple meshes.** The single global `mesh_t mesh` (plus the
  hard-coded cube tables, `load_cube_mesh_data`, and `load_obj_file_data`) is
  replaced by `static mesh_t meshes[MAX_NUM_MESHES]` (MAX = 10) with a new
  API: `load_mesh(obj_filename, png_filename, scale, translation, rotation)`,
  `load_mesh_obj_data`, `load_mesh_png_data`, `get_num_meshes`, `get_mesh`,
  and `free_meshes`. `mesh_t` gains a `texture` member — every mesh owns its
  texture.
- **texture.c — per-mesh textures.** The global `png_texture` /
  `mesh_texture` / `texture_width` / `texture_height` and
  `load_png_texture_data` are gone; texture.c keeps only `tex2_t` /
  `tex2_clone`. `triangle_t` gains a `texture` field, and
  `draw_textured_triangle` / `draw_triangle_texel` now receive the texture
  (`upng_t*`) and query its width/height/pixel buffer per call.
- **main.c — scene loop.** `setup()` calls `load_mesh` twice: f22 at
  translation (-3, 0, +8) and efa at (+3, 0, +8), both scale (1,1,1),
  rotation (0,0,0). `update()` loops `get_num_meshes()` and transforms each
  mesh with its own world matrix. The per-frame mesh animation is commented
  out — the scene is static; only the camera moves.
- **camera.c — encapsulation + pitch.** The `extern camera_t camera` global
  becomes a `static` struct behind `init_camera`, get/update functions for
  position/direction/forward-velocity, `rotate_camera_yaw`, and the new
  `rotate_camera_pitch` (the camera_t struct gains `pitch`). A new
  `get_camera_lookat_target()` builds the camera direction from yaw + pitch
  and returns `position + direction` for `mat4_look_at`.
- **Controls changed.** `w`/`s` now rotate the camera pitch (they used to
  move forward/backward), `left`/`right` arrows rotate the yaw (was `a`/`d`),
  and `up`/`down` arrows move forward/backward along the camera direction
  (they used to move the camera up/down the y-axis).
- **Renames.** `initialize_window` → `init_window`;
  `should_render_wireframe` → `should_render_wire`,
  `should_render_filled_triangles` → `should_render_filled_triangle`,
  `should_render_textured_triangles` → `should_render_textured_triangle`,
  `is_cull_backface` → `should_cull_backface`; `light_apply_intensity` →
  `apply_light_intensity`; `z_near`/`z_far` → `znear`/`zfar`.
  `free_resources` now calls `free_meshes()` + `destroy_window()`.

## Run it

```
cd PYTHON/57/3d_renderer
python main.py               # 800x600 window (default)
python main.py --fullscreen  # borderless desktop-resolution window, like the C step
```

Requires Python ≥ 3.10 with `pygame` and `numpy`.

| Key            | Action                                          |
|----------------|-------------------------------------------------|
| ESC            | quit                                            |
| 1              | wireframe + vertex points                       |
| 2              | wireframe                                       |
| 3              | filled (flat-shaded)                            |
| 4              | filled + wireframe                              |
| 5              | textured                                        |
| 6              | textured + wireframe                            |
| c / x          | backface culling on / off                       |
| w / s          | pitch camera up / down                          |
| left / right   | yaw camera left / right                         |
| up / down      | move camera forward / backward                  |

Test hooks (CONVENTIONS.md §7): `RENDERER_MAX_FRAMES=<n>` exits after n
frames; `RENDERER_SAVE_FRAME=<path.png>` saves the last presented frame;
`SDL_VIDEODRIVER=dummy` works for headless runs.

**Missing models (CONVENTIONS.md §8):** the course repository ships only the
PNG textures — `f22.obj` and `efa.obj` were never committed. Each missing
`.obj` falls back to the built-in cube (parsed from the generated
`assets/cube.obj`), so the default scene shows two textured cubes at the two
mesh transforms. Drop the original course `.obj` files into `assets/` to see
the real airplanes.

## File map

| C file                  | Python file   | Notes                                              |
|-------------------------|---------------|----------------------------------------------------|
| main.c                  | main.py       | game loop + pipeline; loops all meshes             |
| display.c/h             | display.py    | window, buffers, render/cull modes, primitives     |
| mesh.c/h                | mesh.py       | NEW API: mesh array, load_mesh, per-mesh texture   |
| triangle.c/h            | triangle.py   | face/triangle types + rasterizers                  |
| texture.c/h             | texture.py    | tex2_t/tex2_clone + texture_t (replaces upng)      |
| camera.c/h              | camera.py     | encapsulated camera with yaw + pitch               |
| clipping.c/h            | clipping.py   | frustum planes + polygon clipping                  |
| light.c/h               | light.py      | directional light + apply_light_intensity          |
| vector.c/h              | vector.py     | vec2/vec3/vec4 helpers                             |
| matrix.c/h              | matrix.py     | 4x4 matrices, perspective, look-at                 |
| array.c/h               | —             | not ported: Python lists are dynamic arrays        |
| swap.c/h                | —             | not ported: tuple swap `a, b = b, a`               |
| upng.c/h                | —             | not ported: `pygame.image.load` decodes PNGs       |

## Performance notes

NumPy tricks used in this step (CONVENTIONS.md §5):

- `clear_color_buffer` / `clear_z_buffer`: whole-array assignment.
- `draw_grid`: strided slice assignment `buffer[::10, ::10]`.
- `draw_rect`: clipped 2-D slice assignment.
- `draw_line`: DDA via `np.linspace` + one fancy-indexed store.
- Filled and textured triangles: **barycentric bounding-box rasterizer** —
  edge weights for every pixel in the box at once, boolean `inside` mask,
  perspective-correct `1/w`, `u/w`, `v/w` interpolation as array math,
  vectorized z-test, one fancy-indexed store into color- and z-buffer.
- Per mesh, ALL vertices are transformed to camera space with a single
  `(N, 4) @ (4, 4)` matmul per frame (`mesh.homogeneous_vertices`) instead of
  C's three `mat4_mul_vec4` calls per face — a documented improvement.
- Windowed 800x600 default with `--fullscreen` opt-in and the 0.05 s
  delta-time clamp are the documented §7 deviations.
