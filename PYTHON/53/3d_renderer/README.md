# Step 52 — Triangulating the clipped polygon

This step closes the frustum-clipping loop: after each triangle is wrapped in
a `polygon_t` and clipped against all six frustum planes (Sutherland–Hodgman,
implemented in step 51), the clipped polygon is now broken back into
triangles with a fan triangulation, and it is those *clipped* triangles that
are projected and drawn. The step-51 debug line that skipped every face but
index 4 is removed, so the whole cube renders — and it rotates again.

## What changed vs step 51

Derived from the actual C diff (`51/3d_renderer/src` → `52/3d_renderer/src`):

- `clipping.c/h`: new function `triangles_from_polygon()` — fan-triangulates
  the clipped polygon: every triangle shares polygon vertex 0, i.e.
  (0,1,2), (0,2,3), …; n vertices always yield n − 2 triangles. Each output
  vertex is promoted to `vec4` with `vec4_from_vec3` (w = 1).
- `clipping.c/h`: `create_polygon_from_triangle()` is renamed to
  `polygon_from_triangle()`; new constant `MAX_NUM_POLY_TRIANGLES` (10);
  `clipping.h` now includes `triangle.h` (here: `clipping.py` imports
  `triangle_t` from `triangle.py`).
- `main.c`: the step-51 "TODO: break the polygon into triangles" is resolved
  — after `clip_polygon()`, `triangles_from_polygon()` produces
  `triangles_after_clipping`, and the projection / perspective-divide /
  screen-mapping / shading block now runs inside a loop over those triangles
  (projecting `triangle_after_clipping.points[j]` instead of the unclipped
  `transformed_vertices[j]`). The final struct is renamed from
  `projected_triangle` to `triangle_to_render`.
- `main.c`: the debug line `if (i != 4) continue;` is removed — all cube
  faces are processed again.
- `main.c`: the mesh rotates again — rotation velocities go from 0.0/0.0/0.0
  to 0.1/0.2/0.3 rad/s around x/y/z (still at z = 5).
- `clipping.c`: whitespace/comment reformatting of
  `clip_polygon_against_plane` (no behavior change).

## Run it

```
cd PYTHON/52/3d_renderer
python main.py               # 800x600 window (default)
python main.py --fullscreen  # borderless desktop resolution, like the C code
```

| Key            | Action                                             |
|----------------|----------------------------------------------------|
| ESC            | quit                                               |
| 1              | wireframe + vertex points                          |
| 2              | wireframe                                          |
| 3              | filled (flat-shaded)                               |
| 4              | filled + wireframe                                 |
| 5              | textured                                           |
| 6              | textured + wireframe                               |
| c / x          | backface culling on / off                          |
| ↑ / ↓          | move camera up / down                              |
| a / d          | yaw camera left / right                            |
| w / s          | move camera forward / backward                     |

Test hooks (CONVENTIONS.md §7): `RENDERER_MAX_FRAMES=<n>` exits after n
frames; `RENDERER_SAVE_FRAME=<path.png>` saves the last frame;
`SDL_VIDEODRIVER=dummy` runs headless.

## File map

| C file                  | Python file   | Notes                                              |
|-------------------------|---------------|----------------------------------------------------|
| `src/main.c`            | `main.py`     | game loop + pipeline (now loops clipped triangles) |
| `src/display.c/h`       | `display.py`  | window, color/z buffers, primitive drawing         |
| `src/vector.c/h`        | `vector.py`   | vec2/vec3/vec4 helpers                             |
| `src/matrix.c/h`        | `matrix.py`   | 4×4 matrices, perspective, look-at                 |
| `src/light.c/h`         | `light.py`    | directional light + flat-shading intensity         |
| `src/camera.c/h`        | `camera.py`   | global camera struct (position/direction/yaw)      |
| `src/clipping.c/h`      | `clipping.py` | frustum planes, clipping + `triangles_from_polygon` (NEW) |
| `src/texture.c/h`       | `texture.py`  | tex2_t + global mesh texture                       |
| `src/triangle.c/h`      | `triangle.py` | face/triangle types + rasterizers                  |
| `src/mesh.c/h`          | `mesh.py`     | mesh state, cube data, OBJ parser                  |
| `src/array.c/h`         | — not ported  | C dynamic array → Python `list`                    |
| `src/swap.c/h`          | — not ported  | C swap helpers → tuple swap / NumPy sorting        |
| `src/upng.c/h`          | — not ported  | PNG decoding → `pygame.image.load`                 |

Deviation for clarity: C's `triangles_from_polygon(polygon, triangles[],
&count)` fills a caller-provided array plus an out-parameter count; the
Python version returns the list of triangles directly (its length is the
count). Same fan triangulation, same order.

Missing `.obj` fallback (CONVENTIONS.md §8): `assets/cube.obj` is generated
from the course's hard-coded cube so the OBJ parser is genuinely exercised;
if an `.obj` is missing, the built-in cube mesh is loaded instead. Drop the
original course `.obj` files into `assets/` to see the real models.

## Performance notes

NumPy tricks used in this step (CONVENTIONS.md §5):

- `clear_color_buffer` / `clear_z_buffer`: whole-array assignment.
- `draw_grid`: strided slice assignment `buffer[::10, ::10]`.
- `draw_rect`: clipped 2-D slice assignment.
- `draw_line`: DDA vectorized with `np.linspace` + one fancy-indexed store.
- Filled and textured triangles: **barycentric bounding-box rasterizer** —
  edge weights for every pixel in the box at once, boolean-mask z-test,
  perspective-correct 1/w (and u/w, v/w) interpolation as array math, one
  fancy-indexed store into the color and z buffers.
- All mesh vertices are transformed to camera space with a single
  `(N, 4) @ (4, 4)` matmul per frame instead of C's per-face-per-vertex
  `mat4_mul_vec4` (documented improvement).
- Clipping and fan triangulation stay as plain Python loops: they touch at
  most 10 vertices per triangle (per-vertex, not per-pixel work).

Other documented deviations (allowed by CONVENTIONS.md §7/§10): windowed
800×600 default with `--fullscreen` opt-in, delta-time clamped to 0.05 s,
and the input queue fully drained per frame (the C code polls a single
event per frame).
