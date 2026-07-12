# Step 58 — The airport scene

This step assembles the renderer's showcase scene: a runway with three
airplanes (f22, efa, f117) parked on it, rendered **textured by default**
with the far clipping plane pushed out to 50 units. Structurally, the whole
per-mesh pipeline moves out of `update()` into its own
`process_graphics_pipeline_stages(mesh)` function, and the face-normal math
becomes `get_triangle_normal()` in triangle.c — `update()` is now just
"tick the clock, loop the meshes, run the pipeline".

## What changed vs step 57

Derived from the actual C diff (`57/3d_renderer/src` → `58/3d_renderer/src`):

- **main.c — pipeline extracted.** The entire model→world→camera→clipping→
  projection→screen sequence moves from `update()` into a new
  `process_graphics_pipeline_stages(mesh_t*)` function (with a big ASCII
  diagram of the stages). `update()` now only resets the triangle counter and
  calls it per mesh, with commented-out `rotate_mesh_x/y/z(mesh_index, ...)`
  animation lines. The counter is renamed `num_triangles_to_render` →
  `triangles_to_render_count` (the Python version keeps its
  `triangles_to_render` list, so there is no separate counter to rename).
- **main.c — the airport scene.** `setup()` starts in `RENDER_TEXTURED`
  (was `RENDER_WIRE`), `zfar` goes 20 → 50, and four meshes are loaded:
  runway at (0, -1.5, +23), f22 at (0, -1.3, +5), efa at (-2, -1.3, +9) and
  f117 at (+2, -1.3, +9) — the three planes rotated -π/2 around y.
- **main.c — backface culling reorganized.** The normal comes from the new
  `get_triangle_normal(transformed_vertices)`, and the camera-ray/dot-product
  test is computed *inside* the `should_cull_backface()` branch instead of
  unconditionally.
- **triangle.c — `get_triangle_normal`.** New function holding the
  normalize-edges + cross-product face-normal code that used to live inline
  in main.c's update loop. `draw_triangle_pixel` / `draw_triangle_texel` also
  shuffle their parameter order (color/texture moves last) — not applicable
  here because the Python rasterizer is vectorized and never ports those
  per-pixel helpers.
- **mesh.c — capacity and rotation helpers.** `MAX_NUM_MESHES` 10 → 100; new
  `rotate_mesh_x/y/z(mesh_index, angle)` mutators (referenced only from the
  commented-out animation lines); `get_mesh`'s parameter is renamed `index` →
  `mesh_index`; `mesh_t` reorders its members (scale before rotation) and the
  functions are reordered in the file.
- **display.c — half-resolution buffer.** `init_window` re-enables the
  window_width/height override, now `fullscreen_width / 2` and
  `fullscreen_height / 2`: the borderless window still covers the desktop,
  but the color/z buffers are half that size, stretched 2x at present time
  (mirrored in the Python `--fullscreen` path).

## Run it

```
cd PYTHON/58/3d_renderer
python main.py               # 800x600 window (default)
python main.py --fullscreen  # borderless desktop window, half-res buffer scaled 2x, like the C step
```

Requires Python ≥ 3.10 with `pygame` and `numpy`.

| Key            | Action                                          |
|----------------|-------------------------------------------------|
| ESC            | quit                                            |
| 1              | wireframe + vertex points                       |
| 2              | wireframe                                       |
| 3              | filled (flat-shaded)                            |
| 4              | filled + wireframe                              |
| 5              | textured (default)                              |
| 6              | textured + wireframe                            |
| c / x          | backface culling on / off                       |
| w / s          | pitch camera up / down                          |
| left / right   | yaw camera left / right                         |
| up / down      | move camera forward / backward                  |

Test hooks (CONVENTIONS.md §7): `RENDERER_MAX_FRAMES=<n>` exits after n
frames; `RENDERER_SAVE_FRAME=<path.png>` saves the last presented frame;
`SDL_VIDEODRIVER=dummy` works for headless runs.

**Missing models (CONVENTIONS.md §8):** the course repository ships only the
PNG textures — `runway.obj`, `f22.obj`, `efa.obj`, and `f117.obj` were never
committed. Each missing `.obj` falls back to the built-in cube (parsed from
the generated `assets/cube.obj`), so the default scene shows four textured
cubes at the four mesh transforms. Drop the original course `.obj` files into
`assets/` to see the real airport scene.

## File map

| C file                  | Python file   | Notes                                              |
|-------------------------|---------------|----------------------------------------------------|
| main.c                  | main.py       | game loop + process_graphics_pipeline_stages       |
| display.c/h             | display.py    | window, buffers, render/cull modes, primitives     |
| mesh.c/h                | mesh.py       | mesh array (100), rotate_mesh_x/y/z helpers        |
| triangle.c/h            | triangle.py   | face/triangle types, get_triangle_normal, rasters  |
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
