# Step 23 — Loading the F-22 model

The OBJ loader written in the previous step gets its first real model:
`setup()` now loads the course's F-22 jet (`./assets/f22.obj`) instead of the
exported cube. Nothing else changes — the parser, the game loop, and the
green wireframe triangles with yellow vertex dots on top of the grid are all
exactly as in step 22.

## What changed vs step 22

Derived from the actual C diff between `22/` and `23/`:

- **`main.c`**: `setup()` calls `load_obj_file_data("./assets/f22.obj")`
  instead of `load_obj_file_data("./assets/cube.obj")`.
- Everything else is unchanged from step 22 (every other C source file is
  byte-identical).

## Assets (CONVENTIONS.md §8)

The original course repository never committed its `.obj` files, so the C
step 23 cannot actually run as-is (its unchecked `fopen` would crash on the
missing `f22.obj`). In this conversion `load_obj_file_data()` prints a
one-line warning and falls back to the built-in hard-coded cube from
`mesh.py`. The generated `assets/cube.obj` from step 22 still ships here.
Drop the original course `f22.obj` into `assets/` to see the real jet model.

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
| `src/main.c`     | `main.py`     | Game loop, projection, loads `assets/f22.obj`.     |
| `src/display.c`  | `display.py`  | Window, color buffer, grid/pixel/line/triangle/rect. |
| `src/vector.c`   | `vector.py`   | `vec3_rotate_x/y/z`; vectors are NumPy arrays.     |
| `src/mesh.c`     | `mesh.py`     | `mesh_t` dataclass, cube data, `load_obj_file_data()`. |
| `src/triangle.c` | `triangle.py` | `face_t` / `triangle_t` dataclasses (C file is a TODO stub). |
| `src/array.c/h`  | —             | Not ported — Python `list` (+ `append`/`len`) replaces the dynamic array. |

## Performance notes

- `draw_grid`: one strided slice assignment `buffer[::10, ::10] = color`
  replaces the C double loop.
- `draw_rect`: single 2-D slice assignment, clamped to the screen.
- `draw_line` (DDA): all step positions generated at once with
  `np.linspace`, rounded, bounds-masked, and stored with one fancy-indexed
  assignment — no per-pixel Python loop.
- `clear_color_buffer`: `buffer[:] = color`.
- The per-face vertex rotation loop is kept scalar, 1:1 with the C: at
  12 faces × 3 vertices per frame (on the fallback cube) it is not a hot
  path, and side-by-side readability wins (CONVENTIONS.md §5).

Documented improvements (CONVENTIONS.md §10): windowed 800×600 default with
`--fullscreen` opt-in; the input handler drains the whole event queue per
frame instead of the C code's single `SDL_PollEvent` (fixes input lag the C
course itself fixes in a later step); frame cap via `clock.tick(60)`;
missing-`.obj` fallback to the built-in cube instead of the C crash; asset
path resolved relative to `main.py`, not the working directory.
