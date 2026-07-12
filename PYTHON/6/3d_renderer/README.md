# Step 6 — Dotted grid via loop stride

A small but instructive optimization: instead of visiting **every** pixel and
testing `x % 10 == 0 || y % 10 == 0` (step 5), the C loops now *stride* by 10
and touch only the pixels they write. Visually, the solid gray grid lines
become individual white dots at the intersections.

## What changed vs step 5

- `draw_grid()` rewritten: `for (y = 0; y < h; y += 10)` /
  `for (x = 0; x < w; x += 10)` — 4,800 writes instead of 480,000 iterations.
- Dot color is white `0xFFFFFFFF` (was gray `0xFF888888` lines).
- Remaining diff lines are whitespace-only.

## Run it

```
cd PYTHON/6/3d_renderer
py -3.12 main.py               # 800x600 window
py -3.12 main.py --fullscreen  # borderless desktop-resolution, like the C
```

`ESC` or closing the window quits. You should see white dots every 10 px on
black.

## File map

| C file   | Python file | Notes                              |
|----------|-------------|-------------------------------------|
| `main.c` | `main.py`   | everything still lives in one file |
| `Makefile` | —         | nothing to compile                 |

## Performance notes

The C optimization (strided loops) maps to an even stronger numpy form: one
strided 2-D slice assignment `buffer[::10, ::10] = 0xFFFFFFFF` writes all
4,800 dots in a single array operation.
