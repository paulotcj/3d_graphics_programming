# Step 28 — Render modes and culling toggle

This step makes the renderer interactive: keys 1–4 pick what is drawn for
each triangle (wireframe, wireframe + red vertex dots, solid fill, or solid
fill + wireframe), and keys c/d turn backface culling on/off. The fill color
becomes gray `0xFF555555` and the wireframe white `0xFFFFFFFF`; the default
mode is plain wireframe with backface culling enabled.

## What changed vs step 27

Derived from the actual C diff (`27 -> 28`):

- **`display.h`** adds two global enums (declared in the header, C-style):
  - `enum cull_method { CULL_NONE, CULL_BACKFACE }` -> module-level int
    constants + `display.cull_method` in `display.py`.
  - `enum render_method { RENDER_WIRE, RENDER_WIRE_VERTEX,
    RENDER_FILL_TRIANGLE, RENDER_FILL_TRIANGLE_WIRE }` ->
    `display.render_method`.
- **`draw_triangle` moves from `display.c` to `triangle.c`** (declaration
  from `display.h` to `triangle.h`) — mirrored: `draw_triangle` now lives in
  `triangle.py`, not `display.py`.
- **`triangle.h`**: `face_t` gains a `uint32_t color` field; `triangle_t`
  gains `uint32_t color` and `float avg_depth` — declared but not yet used
  by this step's `main.c` (they come alive in the next steps). Mirrored as
  dataclass fields with defaults.
- **`main.c` `setup()`** initializes `render_method = RENDER_WIRE` and
  `cull_method = CULL_BACKFACE`.
- **`main.c` `process_input()`** handles new keys: `1` wire+vertex, `2`
  wire, `3` fill, `4` fill+wire, `c` cull backfaces, `d` no culling.
- **`main.c` `update()`**: the backface-culling block is now wrapped in
  `if (cull_method == CULL_BACKFACE)`.
- **`main.c` `render()`**: adds `SDL_RenderClear(renderer)` (a no-op here —
  pygame has no separate renderer; `clear_color_buffer` already clears),
  then draws per `render_method`: filled triangles in `0xFF555555`,
  wireframe in `0xFFFFFFFF`, and 6×6 red (`0xFFFF0000`) `draw_rect` dots at
  each vertex in `RENDER_WIRE_VERTEX` mode.
- Cosmetic only: whitespace/indentation cleanups in `triangle.c`,
  `display.h`.

## Run it

```
py -3.12 main.py                # 800x600 window (default)
py -3.12 main.py --fullscreen   # borderless desktop-resolution, like the C code
```

| Key | Action |
|-----|--------|
| ESC | Quit |
| 1   | Wireframe + red vertex dots |
| 2   | Wireframe only (default) |
| 3   | Filled triangles |
| 4   | Filled triangles + wireframe |
| c   | Enable backface culling (default) |
| d   | Disable backface culling |

Test hooks: `RENDERER_MAX_FRAMES=<n>` exits after n frames;
`RENDERER_SAVE_FRAME=<path.png>` saves the last frame;
`SDL_VIDEODRIVER=dummy` runs headless.

The C code loads `./assets/cube.obj`, which was never committed to the
original repository — this conversion ships a generated `assets/cube.obj`
(exported from the hard-coded cube in `mesh.c`) so the OBJ parser is
genuinely exercised. If the file is missing, a warning is printed and the
built-in cube mesh is used instead. Drop the original course `.obj` files
into `assets/` to see the real models.

## File map

| C file       | Python file   | Notes                                              |
|--------------|---------------|----------------------------------------------------|
| `main.c`     | `main.py`     | game loop; **new**: mode keys, conditional drawing |
| `display.c`  | `display.py`  | window, color buffer, grid/pixel/line/rect; **new**: render/cull mode globals |
| `vector.c`   | `vector.py`   | vec2/vec3 math, rotations                          |
| `mesh.c`     | `mesh.py`     | cube data, global mesh, OBJ loader                 |
| `triangle.c` | `triangle.py` | filled rasterizer; **new home** of `draw_triangle` |
| `array.c/h`  | — not ported  | C dynamic array -> Python `list`                   |

## Performance notes (CONVENTIONS.md §5)

- `clear_color_buffer` -> `buffer[:] = color` (one vectorized fill).
- `draw_grid` -> one strided slice assignment `buffer[::10, ::10]`.
- `draw_line` (DDA) -> all step positions generated at once with
  `np.linspace`, clipped with a boolean mask, stored with one fancy-indexed
  assignment.
- `draw_rect` (the vertex dots of mode 1) -> one clipped 2-D slice
  assignment per rectangle.
- **Filled triangles**: the C code calls `draw_line` once per scanline (a
  per-pixel DDA). Here each scanline is ONE NumPy slice assignment
  (`buffer[y, x_left:x_right+1] = color`) — identical pixels, and the only
  remaining Python loop is per-scanline, never per-pixel. The midpoint
  split uses `int(...)` truncation to match C integer division exactly.
- Buffers are allocated once in `setup()` and reused every frame.
- Improvements applied (§10): windowed 800x600 default (`--fullscreen`
  restores the C behavior), drain-the-event-queue input polling (the C
  step still polls one event per frame), missing-asset fallback (§8).
