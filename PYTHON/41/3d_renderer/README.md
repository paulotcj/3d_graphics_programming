# Step 40 — Flipped V texture coordinates

A one-change step: the hard-coded cube's per-corner UV coordinates get their
V component flipped (`v` → `1 - v`). Texture images are stored top-down
(row 0 is the top of the picture) while the UV convention used so far had V
growing the other way, so the red-brick texture was rendered upside down.
Flipping V in the face table makes the texture map upright — the rendering
code itself is untouched.

## What changed vs step 39

Derived from the actual C diff (`39/3d_renderer/src` → `40/3d_renderer/src`):

- **`mesh.c`** (the only changed file): every UV in the `cube_faces` table is
  V-flipped. Each face's first triangle goes from
  `(0,0) (0,1) (1,1)` to `(0,1) (0,0) (1,0)`, and the second from
  `(0,0) (1,1) (1,0)` to `(0,1) (1,0) (1,1)`.
- Cosmetic only: a tab in `load_obj_file_data` becomes spaces and the file
  gains a trailing newline (no Python impact).

## Run it

```
cd PYTHON/40/3d_renderer
python main.py               # windowed 800x600 (default)
python main.py --fullscreen  # the C original's borderless desktop-size window
```

| Key   | Action                                        |
|-------|-----------------------------------------------|
| `1`   | Wireframe + red vertex dots                   |
| `2`   | Wireframe only                                |
| `3`   | Filled (flat-shaded)                          |
| `4`   | Filled + wireframe                            |
| `5`   | Textured                                      |
| `6`   | Textured + wireframe (start mode)             |
| `c`   | Enable back-face culling (default)            |
| `d`   | Disable back-face culling                     |
| `ESC` | Quit                                          |

Test hooks (CONVENTIONS.md §7): `RENDERER_MAX_FRAMES=<n>`,
`RENDERER_SAVE_FRAME=<path.png>`, and `SDL_VIDEODRIVER=dummy` all work.

## File map

| C file                  | Python file   | Notes                                                        |
|-------------------------|---------------|--------------------------------------------------------------|
| `src/main.c`            | `main.py`     | game loop, pipeline, painter's-algorithm sort                |
| `src/display.c/h`       | `display.py`  | window, color buffer, grid/pixel/line/rect drawing           |
| `src/vector.c/h`        | `vector.py`   | vec2/vec3/vec4 helpers (incl. `vec2_from_vec4`)              |
| `src/matrix.c/h`        | `matrix.py`   | 4x4 matrices, perspective projection                         |
| `src/light.c/h`         | `light.py`    | directional light + flat-shading intensity                   |
| `src/texture.c/h`       | `texture.py`  | `tex2_t`, 64x64 `REDBRICK_TEXTURE` (zlib+base64, byte-exact) |
| `src/mesh.c/h`          | `mesh.py`     | cube mesh with **V-flipped UVs**, OBJ loader (+ §8 fallback) |
| `src/triangle.c/h`      | `triangle.py` | wire/filled/perspective-correct textured rasterizers         |
| `src/array.c/h`         | — not ported  | C dynamic array → Python `list`                              |
| `src/swap.c/h`          | — not ported  | `int_swap`/`float_swap` → tuple swap; rasterizer needs no sort |

The original course `.obj` files were never committed; drop them into
`assets/` to load real models (`load_obj_file_data` falls back to the
built-in cube when a file is missing). This step's C hard-codes the texture
and calls `load_cube_mesh_data()` anyway.

## Performance notes (CONVENTIONS.md §5)

- `clear_color_buffer` → `buffer[:] = color`; `draw_grid` → strided slice
  `buffer[::10, ::10]`; `draw_rect` → clipped 2-D slice assignment;
  `draw_line` → `np.linspace` DDA with one fancy-indexed store.
- Filled and textured triangles use the **barycentric bounding-box
  rasterizer**: the C scanline loops (and the per-pixel `draw_texel`) become
  array math over the triangle's bounding box — weights, `u/w`, `v/w`, `1/w`
  interpolation, and the texture sample (`texels[tex_y, tex_x]` fancy
  indexing) all happen for every covered pixel at once.
- All mesh vertices are transformed with **one matmul per frame**
  (`homogeneous @ world_matrix.T`) instead of C's per-face-per-vertex
  multiplies; the world matrix itself is built once per frame instead of
  once per vertex (same product).
- Texel lookup adds a `% texture_width` wrap: the C code's
  `abs((int)(u * 64))` reads one texel out of bounds when `u == 1.0`
  (harmless undefined behavior in C, an `IndexError` in NumPy).
- Event handling drains the whole queue instead of C's single
  `SDL_PollEvent` per frame (allowed input-lag fix, §10).
