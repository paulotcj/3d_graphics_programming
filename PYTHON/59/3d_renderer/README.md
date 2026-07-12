# Step 59 — Full-resolution final renderer

The last step of the course: the complete software 3D renderer. A scene of
four textured meshes (a runway and three jets) travels the whole pipeline
every frame — world and view transforms, backface culling, frustum clipping
with UV interpolation, perspective projection, and perspective-correct
z-buffered texture mapping — with a free-flying FPS-style camera.

## What changed vs step 58

- `display.c`: the window now covers the **full desktop resolution** instead
  of half of it (`window_width = fullscreen_width` replaces
  `fullscreen_width / 2`; same for the height). That is the entire C diff —
  the rendering code is unchanged.
- Python note: per CONVENTIONS.md §7 this conversion defaults to a friendly
  800×600 window; pass `--fullscreen` to reproduce the C step's borderless
  full-desktop window.

## Run it

```
cd PYTHON/59/3d_renderer
py -3.12 main.py               # 800x600 window (development default)
py -3.12 main.py --fullscreen  # borderless full desktop, like the C step
```

| Key            | Action                                       |
|----------------|----------------------------------------------|
| ESC            | quit                                         |
| 1              | wireframe + red vertex dots                  |
| 2              | wireframe                                    |
| 3              | filled (flat-shaded)                         |
| 4              | filled + wireframe                           |
| 5              | textured                                     |
| 6              | textured + wireframe                         |
| c / x          | backface culling on / off                    |
| w / s          | pitch camera up / down                       |
| ← / →          | yaw camera left / right                      |
| ↑ / ↓          | move forward / backward along view direction |

Test hooks (CONVENTIONS.md §7): `RENDERER_MAX_FRAMES=<n>` exits after n
frames, `RENDERER_SAVE_FRAME=<path.png>` saves the last presented frame, and
`SDL_VIDEODRIVER=dummy` runs headless.

**Missing models:** the course's `.obj` files (`runway.obj`, `f22.obj`,
`efa.obj`, `f117.obj`) were never committed to this repository — only the PNG
textures. Each missing mesh falls back (with a one-line warning) to the
built-in cube, parsed from the generated `assets/cube.obj` so the OBJ loader
is still exercised, textured with that mesh's own PNG. Drop the original
course `.obj` files into `assets/` to see the real models.

## File map

| C file                  | Python file   | Notes                                                        |
|-------------------------|---------------|--------------------------------------------------------------|
| `src/main.c`            | `main.py`     | game loop + pipeline stages                                  |
| `src/display.c/h`       | `display.py`  | window, color/z buffers, grid/pixel/line/rect                |
| `src/vector.c/h`        | `vector.py`   | vec2/vec3/vec4 helpers                                       |
| `src/matrix.c/h`        | `matrix.py`   | 4×4 matrices, perspective, look-at                           |
| `src/mesh.c/h`          | `mesh.py`     | mesh array, OBJ parsing, §8 fallback                         |
| `src/triangle.c/h`      | `triangle.py` | face/triangle types + rasterizers                            |
| `src/light.c/h`         | `light.py`    | directional light, flat-shading intensity                    |
| `src/camera.c/h`        | `camera.py`   | FPS camera (yaw/pitch/look-at target)                        |
| `src/clipping.c/h`      | `clipping.py` | frustum planes + polygon clipping                            |
| `src/texture.c/h`       | `texture.py`  | `tex2_t` + texture image type                                |
| `src/upng.c/h`          | —             | not ported — replaced by `pygame.image.load` (texture.py)    |
| `src/array.c/h`         | —             | not ported — replaced by Python lists                        |
| `src/swap.c/h`          | —             | not ported — tuple swap `a, b = b, a` (unused after the barycentric rasterizer) |

## Performance notes

NumPy tricks used in this step (CONVENTIONS.md §5):

- **Barycentric bounding-box rasterizer** (`triangle.py`) for both filled and
  textured triangles: barycentric weights for every pixel of the bounding box
  in one broadcasted expression, `inside` mask, vectorized `1/w` z-test
  against a z-buffer slice, and one fancy-indexed store. Texel fetches are a
  single fancy-indexed lookup into the `(h, w)` uint32 `0xAARRGGBB` texel
  array. The z-buffer stores `1 - interpolated(1/w)` (cleared to 1.0, closer
  pixels are smaller — same comparison direction as the C code).
- **Perspective-correct interpolation**: `u/w`, `v/w`, and `1/w` are linear
  in screen space, so they are interpolated as arrays and each pixel recovers
  `u = (u/w) / (1/w)` — identical math to `draw_triangle_texel`, vectorized.
- **Batched vertex transform** (`main.py`): view × world is combined once per
  mesh and all N vertices are transformed with a single
  `vertices @ (view @ world).T` matmul per frame, instead of C's
  per-face-per-vertex `mat4_mul_vec4` (also rebuilt world per vertex).
- Vectorized `draw_line` (np.linspace DDA), `draw_grid` (strided slice),
  `draw_rect` (2-D slice), and buffer clears (`buffer[:] = value`).
- Buffers are allocated once at startup and reused every frame.

Deliberate deviations (all behavior-preserving, per CONVENTIONS.md §10):
windowed 800×600 default with `--fullscreen` opt-in, `delta_time` clamped to
0.05 s, missing-asset fallback, and `triangles_from_polygon` returning a
Python list instead of filling a caller-provided array.
