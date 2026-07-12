# Step 5 — Drawing a grid in the color buffer

The first step that draws its own pixels. `draw_grid()` writes gray
(`0xFF888888`) pixels into the color buffer on every 10th row and column —
rendering is now literally "writing numbers into our own array", which is the
foundation every later drawing routine builds on.

## What changed vs step 4

- Added `draw_grid()`: the C version loops over **every** pixel and tests
  `x % 10 == 0 || y % 10 == 0`.
- `render()` now calls `draw_grid()` before presenting the buffer.
- The buffer clear color changed from the debug yellow `0xFFFFFF00` to black
  `0xFF000000`.
- The redundant `SDL_SetRenderDrawColor` + `SDL_RenderClear` pair was removed
  from `render()` — the color buffer covers the whole window already.
- (The rest of the C diff is brace-style cleanup with no behavior change.)

## Run it

```
cd PYTHON/5/3d_renderer
py -3.12 main.py               # 800x600 window
py -3.12 main.py --fullscreen  # borderless desktop-resolution, like the C
```

`ESC` or closing the window quits. You should see a gray grid on black.

## File map

| C file   | Python file | Notes                                   |
|----------|-------------|-----------------------------------------|
| `main.c` | `main.py`   | everything still lives in one file      |
| `Makefile` | —         | nothing to compile                      |

## Performance notes

`draw_grid()` is the first real use of the CONVENTIONS.md §5 playbook: the C
double loop over 800×600 = 480,000 pixels becomes **two strided numpy slice
assignments** (`buffer[::10, :]` and `buffer[:, ::10]`) that write exactly
the same pixels. `clear_color_buffer()` is a single broadcast assignment.
