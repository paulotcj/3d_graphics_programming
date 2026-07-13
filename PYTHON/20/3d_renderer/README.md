# Step 20 — Dynamic arrays for triangles to render

Visually identical to step 19 (spinning green wireframe cube), but the
fixed-size `triangle_t triangles_to_render[N_MESH_FACES]` becomes a
**dynamic array**, rebuilt every frame with the `array.c` helpers
(`array_push` / `array_length` / `array_free`). This flexibility is the
groundwork for meshes of any size — OBJ loading arrives in step 22.

## What changed vs step 19

- `main.c`: `triangles_to_render` is now `triangle_t*` (NULL each frame,
  grown with `array_push`, iterated with `array_length`, freed with
  `array_free`).
- `array.c`/`array.h` are now actually used (added in step 19).

## The Python side

A Python `list` **is** a dynamic array, so the mapping is one-to-one and
`array.c` needs no port (CONVENTIONS.md §2):

| C                      | Python                        |
|------------------------|-------------------------------|
| `array_push(arr, x)`   | `arr.append(x)`               |
| `array_length(arr)`    | `len(arr)`                    |
| `array_free(arr)`      | `arr.clear()` / garbage collector |

## Run it

```
cd PYTHON/20/3d_renderer
py -3.12 main.py               # 800x600 window
py -3.12 main.py --fullscreen  # borderless desktop-resolution, like the C
```

`ESC` or closing the window quits.

## File map

| C file          | Python file   | Notes                                  |
|-----------------|---------------|-----------------------------------------|
| `main.c`        | `main.py`     | dynamic triangles_to_render list       |
| `display.c/.h`  | `display.py`  | drawing helpers (unchanged)            |
| `vector.c/.h`   | `vector.py`   | vec2/vec3 + rotations (unchanged)      |
| `mesh.c/.h`     | `mesh.py`     | cube mesh (unchanged)                  |
| `triangle.c/.h` | `triangle.py` | `face_t`, `triangle_t` (unchanged)     |
| `array.c/.h`    | —             | Python `list` (see table above)        |
| `Makefile`      | —             | nothing to compile                     |

## Performance notes

Unchanged from step 19 — vectorized DDA lines, 60 FPS cap.
