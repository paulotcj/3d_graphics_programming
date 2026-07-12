# Step 27 — Filled triangles (flat-top / flat-bottom rasterization)

This step turns the wireframe cube into a *solid* one. Every projected face
is now filled with the classic flat-top/flat-bottom scanline technique: sort
the vertices by y, split the triangle at the middle vertex, and sweep two
edge slopes one scanline at a time. A black wireframe is drawn on top of each
white filled triangle so the individual faces remain visible.

## What changed vs step 26

Derived from the actual C diff (`26 -> 27`):

- **`triangle.c` gains its implementation** (it was a TODO stub in step 26):
  - `int_swap` helper (Python: tuple swap, not ported as a function).
  - `fill_flat_bottom_triangle` — walks two inverse slopes from the top
    vertex down, drawing one horizontal line per scanline.
  - `fill_flat_top_triangle` — same idea, from the bottom vertex up.
  - `draw_filled_triangle` — sorts the three vertices by y, then either
    fills a single flat half or splits the triangle at midpoint
    `(Mx, My)` (triangle similarity) into a flat-bottom + flat-top pair.
- **`triangle.h`** declares `draw_filled_triangle` (and includes `<stdint.h>`).
- **`main.c` `render()`**: each triangle is now drawn twice — first
  `draw_filled_triangle(..., 0xFFFFFFFF)` (solid white), then the existing
  `draw_triangle` outline with its color changed from green `0xFF00FF00` to
  black `0xFF000000`.
- **`main.c` `update()`**: z rotation speed changed from `0.02` to `0.01`
  (all three axes now rotate at `0.01`/frame).
- Cosmetic only: whitespace/indentation cleanups in `display.c`,
  `vector.c`, `vector.h`, and a `{0,0,0}` -> designated-initializer change
  for `camera_position`.

## Run it

```
py -3.12 main.py                # 800x600 window (default)
py -3.12 main.py --fullscreen   # borderless desktop-resolution, like the C code
```

| Key | Action |
|-----|--------|
| ESC | Quit   |

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

| C file       | Python file   | Notes                                             |
|--------------|---------------|---------------------------------------------------|
| `main.c`     | `main.py`     | game loop, transform + cull + project pipeline    |
| `display.c`  | `display.py`  | window, color buffer, grid/pixel/line/rect        |
| `vector.c`   | `vector.py`   | vec2/vec3 math, rotations                         |
| `mesh.c`     | `mesh.py`     | cube data, global mesh, OBJ loader                |
| `triangle.c` | `triangle.py` | **new**: flat-top/flat-bottom filled rasterizer   |
| `array.c/h`  | — not ported  | C dynamic array -> Python `list`                  |

## Performance notes (CONVENTIONS.md §5)

- `clear_color_buffer` -> `buffer[:] = color` (one vectorized fill).
- `draw_grid` -> one strided slice assignment `buffer[::10, ::10]`.
- `draw_line` (DDA) -> all step positions generated at once with
  `np.linspace`, clipped with a boolean mask, stored with one fancy-indexed
  assignment.
- **Filled triangles**: the C code calls `draw_line` once per scanline (a
  per-pixel DDA). Here each scanline is ONE NumPy slice assignment
  (`buffer[y, x_left:x_right+1] = color`) — identical pixels, and the only
  remaining Python loop is per-scanline, never per-pixel. The midpoint
  split uses `int(...)` truncation to match C integer division exactly.
- Buffers are allocated once in `setup()` and reused every frame.
- Improvements applied (§10): windowed 800x600 default (`--fullscreen`
  restores the C behavior), drain-the-event-queue input polling (the C
  step still polls one event per frame), missing-asset fallback (§8).
