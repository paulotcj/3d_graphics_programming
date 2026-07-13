# Step 19 — Line drawing (DDA) and wireframe triangles

The cube finally looks like a cube. `display.py` gains `draw_line()` — the
**DDA algorithm**: pick the longest axis between the endpoints, take that
many unit steps, accumulating a fixed fractional increment on the other axis
— and `draw_triangle()`, which traces three lines. `render()` now draws every
projected face as a green wireframe over the yellow vertex markers.

## What changed vs step 18

- `display.c`: new `draw_line(x0, y0, x1, y1, color)` (DDA) and
  `draw_triangle(...)` → mirrored in [display.py](display.py).
- `main.c` `render()`: after the three vertex rects, draws the unfilled
  triangle in green `0xFF00FF00`.
- New `array.c`/`array.h`: a hand-rolled C dynamic array (capacity headers
  before the data pointer). **Not used until step 20**, and never ported —
  Python's `list` is the same thing built in (CONVENTIONS.md §2).

## Run it

```
cd PYTHON/19/3d_renderer
py -3.12 main.py               # 800x600 window
py -3.12 main.py --fullscreen  # borderless desktop-resolution, like the C
```

`ESC` or closing the window quits. You should see a spinning green wireframe
cube with yellow corner markers.

## File map

| C file          | Python file   | Notes                                  |
|-----------------|---------------|-----------------------------------------|
| `main.c`        | `main.py`     | game loop, face transform + project    |
| `display.c/.h`  | `display.py`  | + `draw_line` (DDA), `draw_triangle`   |
| `vector.c/.h`   | `vector.py`   | vec2/vec3 + rotation functions         |
| `mesh.c/.h`     | `mesh.py`     | hard-coded cube vertices + faces       |
| `triangle.c/.h` | `triangle.py` | `face_t`, `triangle_t` dataclasses     |
| `array.c/.h`    | —             | C dynamic array; Python `list` instead |
| `Makefile`      | —             | nothing to compile                     |

## Performance notes

`draw_line` is vectorized (CONVENTIONS.md §5): `np.linspace` generates every
step position of the DDA at once, `floor(v + 0.5)` reproduces C `round()`,
an on-screen mask replaces the per-pixel bounds check, and one fancy-indexed
assignment writes the whole line. 36 lines/frame renders at the 60 FPS cap.
