# Step 21 — Dynamic mesh structure

The spinning wireframe cube looks identical to step 20, but under the hood
the mesh stops being a pair of fixed-size global arrays and becomes a
dynamic `mesh_t` structure: growable vertex and face lists plus a per-mesh
rotation. This is the refactor that makes the next step — loading arbitrary
`.obj` models from disk — possible.

## What changed vs step 20

Derived from the actual C diff between `20/` and `21/`:

- **`mesh.h` / `mesh.c`**: new `mesh_t` struct (`vertices`, `faces`,
  `rotation`) with a global `mesh` instance. The static cube data is renamed
  `mesh_vertices`/`mesh_faces` → `cube_vertices`/`cube_faces`
  (`N_MESH_*` → `N_CUBE_*`), and a new `load_cube_mesh_data()` pushes the
  static cube data into the dynamic mesh with `array_push`.
- **`main.c`**: the global `cube_rotation` is removed — rotation now lives in
  `mesh.rotation`. `setup()` calls `load_cube_mesh_data()`. `update()` loops
  `array_length(mesh.faces)` instead of the compile-time `N_MESH_FACES`, and
  indexes `mesh.vertices` / `mesh.faces`. A new `free_resources()`
  (color buffer + mesh arrays) runs after `destroy_window()`.
- **`display.c`**: `free(color_buffer)` moves out of `destroy_window()` into
  the new `free_resources()`. Everything else is comment cleanup only.
- **`vector.c/h`, `display.h`**: comment cleanup only — no behavior change.

## Run it

```
py -3.12 main.py               # 800x600 window (default)
py -3.12 main.py --fullscreen  # borderless desktop resolution, like the C code
```

| Control | Action |
|---------|--------|
| ESC     | quit   |

Test hooks (CONVENTIONS.md §7): `RENDERER_MAX_FRAMES=<n>` exits after n
frames; `RENDERER_SAVE_FRAME=<path.png>` saves the final frame.

## File map

| C file           | Python file   | Notes                                              |
|------------------|---------------|----------------------------------------------------|
| `src/main.c`     | `main.py`     | Game loop, projection, `free_resources()`.         |
| `src/display.c`  | `display.py`  | Window, color buffer, grid/pixel/line/triangle/rect. |
| `src/vector.c`   | `vector.py`   | `vec3_rotate_x/y/z`; vectors are NumPy arrays.     |
| `src/mesh.c`     | `mesh.py`     | `mesh_t` dataclass, cube data, `load_cube_mesh_data()`. |
| `src/triangle.c` | `triangle.py` | `face_t` / `triangle_t` dataclasses (C file is a TODO stub). |
| `src/array.c/h`  | —             | Not ported — Python `list` (+ `append`/`len`) replaces the dynamic array. |

No assets: the cube mesh is hard-coded; OBJ loading arrives in step 22.

## Performance notes

- `draw_grid`: one strided slice assignment `buffer[::10, ::10] = color`
  replaces the C double loop.
- `draw_rect`: single 2-D slice assignment, clamped to the screen.
- `draw_line` (DDA): all step positions generated at once with
  `np.linspace`, rounded, bounds-masked, and stored with one fancy-indexed
  assignment — no per-pixel Python loop.
- `clear_color_buffer`: `buffer[:] = color`.
- The per-face vertex rotation loop is kept scalar, 1:1 with the C: at
  12 faces × 3 vertices per frame it is not a hot path, and side-by-side
  readability wins (CONVENTIONS.md §5).

Documented improvements (CONVENTIONS.md §10): windowed 800×600 default with
`--fullscreen` opt-in; the input handler drains the whole event queue per
frame instead of the C code's single `SDL_PollEvent` (fixes input lag the C
course itself fixes in a later step); frame cap via `clock.tick(60)`.
