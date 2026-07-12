# Step 39 — Perspective-correct texture mapping

This step fixes the texture distortion of step 38. Affine interpolation of
u and v is wrong under perspective: equal steps across the *screen* are not
equal steps across the *3D surface*. The projected vertices now carry their
full `(x, y, z, w)` — `w` holds the original camera-space depth — and the
textured rasterizer interpolates `u/w`, `v/w`, and `1/w` (which ARE linear
in screen space), recovering `u = (u/w)/(1/w)` per pixel. The red-brick
cube now rotates slowly around y only, so the fix is easy to see on the big
front face: no more warping along the triangle diagonal.

## What changed vs step 38

Derived from the actual C diff (`38/3d_renderer/src` → `39/3d_renderer/src`):

- **`triangle.h`**: `triangle_t.points` grows from `vec2_t[3]` to
  `vec4_t[3]`, and `draw_textured_triangle` gains `z` and `w` parameters for
  every vertex.
- **`triangle.c`**: `draw_texel` now takes the three `vec4_t` points plus
  `tex2_t` UVs and performs the **perspective-correct** interpolation —
  `u/w`, `v/w`, and `1/w` are combined with the barycentric weights, then
  divided back by the interpolated `1/w`. The vertex sort in
  `draw_textured_triangle` also swaps `z` and `w` alongside x/y/u/v.
- **`vector.c/h`**: (already present since step 38) `vec2_from_vec4` is used
  by `draw_texel` to get the 2D screen points.
- **`main.c`**: `setup()` now also sets `texture_width = texture_height = 64`
  when pointing `mesh_texture` at `REDBRICK_TEXTURE`; the projected triangle
  stores all four components of each projected point; the animation changes
  from `+0.002` on all three axes to **y-only `+0.003`**; the
  `RENDER_WIRE_VERTEX` rects change color `0xFF0000FF` (blue) →
  `0xFFFF0000` (red).
- **`texture.c/h`**: declaration reshuffling only, no behavior change.

## Run it

```
cd PYTHON/39/3d_renderer
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
| `src/mesh.c/h`          | `mesh.py`     | cube mesh with UVs, OBJ loader (+ §8 missing-file fallback)  |
| `src/triangle.c/h`      | `triangle.py` | wire/filled/**perspective-correct textured** rasterizers     |
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
