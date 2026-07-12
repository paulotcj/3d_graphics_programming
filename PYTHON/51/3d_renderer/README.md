# Step 51 — Clipping a polygon against the frustum planes

This step implements the heart of frustum clipping: the Sutherland–Hodgman
routine that clips a polygon against a single plane, applied in sequence to
all six frustum planes. Each triangle is wrapped in a `polygon_t` and clipped
in camera space — but the clipped result is **not used yet** (breaking the
polygon back into triangles is the next lesson), so the original triangle is
still the one projected and drawn. To make the clipping easy to observe, the
C code also carries a debug line that skips every face except index 4, so
only one triangle of the cube is processed.

## What changed vs step 50

Derived from the actual C diff (`50/3d_renderer/src` → `51/3d_renderer/src`):

- `clipping.c`: `clip_polygon_against_plane()` gets its real implementation
  (it was a `TODO` stub in step 50) — walk the polygon edges, keep vertices
  with `dot(Q - P, N) > 0`, and insert the intersection point
  `I = prev + t * (cur - prev)` with `t = prev_dot / (prev_dot - cur_dot)`
  whenever an edge crosses the plane. The result replaces the polygon's
  vertex list in place.
- `vector.c/h`: new helper `vec3_clone()` (returns a copy of a vec3), used by
  the clipping routine.
- `main.c`: the face loop gains the debug line `if (i != 4) continue;` —
  only face index 4 of the cube is transformed, clipped, and rendered.
- `main.c`: still `TODO: after clipping, we need to break the polygon into
  triangles` — the projected triangle is built from the *unclipped*
  transformed vertices, exactly as in step 50.

Note: face index 4 of `cube.obj` is the first back-face triangle
(`f 6 5 7`, normal facing +z). With the default backface culling on, it is
culled and only the grid is visible — press `x` to disable culling and see
the triangle (this matches the C program's behavior exactly).

## Run it

```
cd PYTHON/51/3d_renderer
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
| `src/main.c`            | `main.py`     | game loop + pipeline (incl. the `i != 4` debug skip) |
| `src/display.c/h`       | `display.py`  | window, color/z buffers, primitive drawing         |
| `src/vector.c/h`        | `vector.py`   | vec2/vec3/vec4 helpers (+ new `vec3_clone`)        |
| `src/matrix.c/h`        | `matrix.py`   | 4×4 matrices, perspective, look-at                 |
| `src/light.c/h`         | `light.py`    | directional light + flat-shading intensity         |
| `src/camera.c/h`        | `camera.py`   | global camera struct (position/direction/yaw)      |
| `src/clipping.c/h`      | `clipping.py` | frustum planes + Sutherland–Hodgman clipping (NEW) |
| `src/texture.c/h`       | `texture.py`  | tex2_t + global mesh texture                       |
| `src/triangle.c/h`      | `triangle.py` | face/triangle types + rasterizers                  |
| `src/mesh.c/h`          | `mesh.py`     | mesh state, cube data, OBJ parser                  |
| `src/array.c/h`         | — not ported  | C dynamic array → Python `list`                    |
| `src/swap.c/h`          | — not ported  | C swap helpers → tuple swap / NumPy sorting        |
| `src/upng.c/h`          | — not ported  | PNG decoding → `pygame.image.load`                 |

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
- The clipping routine itself stays as a plain Python loop: it touches at
  most 10 vertices per triangle (per-vertex, not per-pixel work).

Other documented deviations (allowed by CONVENTIONS.md §7/§10): windowed
800×600 default with `--fullscreen` opt-in, delta-time clamped to 0.05 s,
and the input queue fully drained per frame (the C code polls a single
event per frame).
