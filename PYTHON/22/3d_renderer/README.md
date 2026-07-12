# Step 22 — OBJ file loading

The renderer stops hard-coding its geometry: a new `load_obj_file_data()`
parses a Wavefront `.obj` file from disk into the dynamic `mesh_t` structure
introduced in step 21, and `setup()` loads `./assets/cube.obj` instead of
calling `load_cube_mesh_data()`. Visually the result is the same spinning
green wireframe cube — but the mesh could now be any triangulated model.

## What changed vs step 21

Derived from the actual C diff between `21/` and `22/`:

- **`mesh.c` / `mesh.h`**: new `load_obj_file_data(char* filename)` — reads
  the file line by line; `v x y z` lines become vertices (`sscanf
  "v %f %f %f"`), `f v/vt/vn v/vt/vn v/vt/vn` lines become faces (`sscanf
  "f %d/%d/%d ..."`), keeping only the three (1-based) vertex indices and
  discarding the texture/normal indices. `load_cube_mesh_data()` and the
  static cube tables remain but are no longer called from setup.
- **`main.c`**: `setup()` replaces `load_cube_mesh_data()` with
  `load_obj_file_data("./assets/cube.obj")` (the old call is left commented
  out, mirrored here).
- Everything else is unchanged from step 21.

## Assets (CONVENTIONS.md §8)

The original course repository never committed its `.obj` files, so the C
step 22 cannot actually run as-is (its unchecked `fopen` would crash).
This conversion ships a generated `assets/cube.obj` — the same 8-vertex /
12-face cube from `mesh.c`, exported in the exact `f v/vt/vn` face format
the step-22 parser expects — so the OBJ parser is genuinely exercised. If
the file is missing, a one-line warning is printed and the built-in cube is
loaded instead. Drop the original course `.obj` files into `assets/` (and
point `setup()` at them) to see the real models.

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
| `src/main.c`     | `main.py`     | Game loop, projection, loads `assets/cube.obj`.    |
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
  12 faces × 3 vertices per frame it is not a hot path, and side-by-side
  readability wins (CONVENTIONS.md §5).

Documented improvements (CONVENTIONS.md §10): windowed 800×600 default with
`--fullscreen` opt-in; the input handler drains the whole event queue per
frame instead of the C code's single `SDL_PollEvent` (fixes input lag the C
course itself fixes in a later step); frame cap via `clock.tick(60)`;
missing-`.obj` fallback to the built-in cube instead of the C crash; asset
path resolved relative to `main.py`, not the working directory.
