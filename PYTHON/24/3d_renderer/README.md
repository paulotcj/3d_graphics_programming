# Step 24 — Vector math operations (add, sub, dot, cross)

`vector.py` grows from just the rotation helpers into the full toolbox the
renderer leans on from here on: `length`, `add`, `sub`, `mul`, `div` for both
vec2 and vec3, plus the 3D **dot product** (how aligned two vectors are) and
**cross product** (the perpendicular vector — soon to be the face normal).
Dot and cross are the two workhorses behind backface culling in step 25.

## What changed vs step 23

- `vector.c`/`vector.h`: implementations + prototypes for
  `vec2_length/add/sub/mul/div/dot` and `vec3_length/add/sub/mul/div/cross/dot`.
- `main.c` `setup()`: a small demo computing two lengths and a `vec3_add`
  (results unused — a sanity check of the new library, mirrored verbatim).
- Mesh rotation restricted to the **x axis only** (y/z increments set to 0),
  making the upcoming culling behavior easier to observe.

## Run it

```
cd PYTHON/24/3d_renderer
py -3.12 main.py               # 800x600 window
py -3.12 main.py --fullscreen  # borderless desktop-resolution, like the C
```

`ESC` or closing the window quits (`H` shows the key help). The F-22
stand-in model tumbles around the x axis as a green wireframe.

> **Model note:** the real course models are included in this step's
> `assets/` folder and load through the normal OBJ parser, exactly as in the
> C course. If a model file is ever removed, the loader prints a one-line
> warning and falls back to the built-in cube so the step still runs.

## File map

| C file          | Python file   | Notes                                   |
|-----------------|---------------|------------------------------------------|
| `main.c`        | `main.py`     | + vector demo in setup, x-only rotation |
| `vector.c/.h`   | `vector.py`   | **the full vec2/vec3 math library**     |
| `display.c/.h`  | `display.py`  | unchanged                               |
| `mesh.c/.h`     | `mesh.py`     | OBJ loader (cosmetic cleanup in C)      |
| `triangle.c/.h` | `triangle.py` | unchanged                               |
| `array.c/.h`    | —             | Python `list`                           |
| `Makefile`      | —             | nothing to compile                      |

## Performance notes

The scalar vector helpers mirror the C 1:1 for readability; they operate on
a handful of vertices per face. All per-pixel work stays vectorized
(CONVENTIONS.md §5). Runs at the 60 FPS cap.
