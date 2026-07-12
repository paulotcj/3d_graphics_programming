# Step 29 — Painter's algorithm (sorted face depth) and per-face colors

This step introduces visible-surface ordering: each projected triangle now
carries its face color and the average z-depth of its three transformed
vertices, and the triangle list is sorted back-to-front before rendering so
nearer faces paint over farther ones (the painter's algorithm). The demo mesh
switches back to the hard-coded cube, whose six sides are now individually
colored, so pressing `3` shows a solid multi-colored spinning cube.

## What changed vs step 28

Derived from the actual C diff (`28 -> 29`):

- **`mesh.c`**: every entry of `cube_faces` gains a `.color` — red front
  (`0xFFFF0000`), green right (`0xFF00FF00`), blue back (`0xFF0000FF`),
  yellow left (`0xFFFFFF00`), magenta top (`0xFFFF00FF`), cyan bottom
  (`0xFF00FFFF`).
- **`main.c` `setup()`**: calls `load_cube_mesh_data()` again;
  `load_obj_file_data("./assets/cube.obj")` is commented out (the OBJ loader
  does not read colors, so the colored cube is used instead).
- **`main.c` `update()`**:
  - the projection loop writes into a local `vec2_t projected_points[3]`
    array instead of filling `projected_triangle.points` directly;
  - computes `avg_depth = (z0 + z1 + z2) / 3.0` from the transformed
    vertices;
  - builds `projected_triangle` with `.points`, `.color = mesh_face.color`,
    and `.avg_depth`;
  - after the face loop, sorts `triangles_to_render` by `avg_depth`,
    largest first (back-to-front), with a hand-rolled O(n²) swap sort — the
    Python version uses `list.sort(key=..., reverse=True)` for the same
    order (documented improvement, §10).
- **`main.c` `render()`**: filled triangles are drawn with `triangle.color`
  instead of the hard-coded gray `0xFF555555`.
- **`triangle.h`**: whitespace/indentation cleanup only (the `color` and
  `avg_depth` fields already existed since step 28; this step starts using
  them).

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
| 3   | Filled triangles (per-face colors) |
| 4   | Filled triangles + wireframe |
| c   | Enable backface culling (default) |
| d   | Disable backface culling |

Test hooks: `RENDERER_MAX_FRAMES=<n>` exits after n frames;
`RENDERER_SAVE_FRAME=<path.png>` saves the last frame;
`SDL_VIDEODRIVER=dummy` runs headless.

Like the C code, this step loads the built-in cube (`load_cube_mesh_data`),
not an OBJ file; `assets/cube.obj` is kept from the previous step (and the
OBJ-loader fallback of §8 remains in `mesh.py`) so switching the commented
lines in `setup()` works, matching the C source.

## File map

| C file       | Python file   | Notes                                                    |
|--------------|---------------|----------------------------------------------------------|
| `main.c`     | `main.py`     | game loop; **new**: avg_depth + back-to-front sort       |
| `display.c`  | `display.py`  | window, color buffer, grid/pixel/line/rect, mode globals |
| `vector.c`   | `vector.py`   | vec2/vec3 math, rotations                                |
| `mesh.c`     | `mesh.py`     | cube data (**new**: per-face colors), global mesh, OBJ loader |
| `triangle.c` | `triangle.py` | flat-top/flat-bottom rasterizer, `draw_triangle`         |
| `array.c/h`  | — not ported  | C dynamic array -> Python `list`                         |

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
- **Depth sort**: the C step's O(n²) swap sort becomes Python's built-in
  Timsort (`list.sort` with `reverse=True`) — same back-to-front result,
  O(n log n).
- Buffers are allocated once in `setup()` and reused every frame.
- Improvements applied (§10): windowed 800x600 default (`--fullscreen`
  restores the C behavior), drain-the-event-queue input polling (the C
  step still polls one event per frame), missing-asset fallback (§8).
