# Step 7 — Drawing rectangles

This step adds the first real drawing routine on top of step 6's color-buffer
machinery: `draw_rect`, a function that scans a rectangular region of the
color buffer column by column. Each frame still draws the 10-pixel dotted
grid, and now also a 300x150 rectangle at (300, 200). The step's `draw_rect`
intentionally overwrites the color argument with a per-column counter, so the
rectangle appears as a barely-visible dark gradient rather than the magenta
`0xFFFF00FF` passed at the call site — a quirk of this step's C code that the
port reproduces exactly.

## What changed vs step 6

Derived from the actual C diff (`6/3d_renderer/src/main.c` → `7/3d_renderer/src/main.c`):

- Added `draw_rect(x, y, width, height, color)`: a double loop that fills the
  rectangle column by column. It resets `color` to 0 and increments it once
  per column, so column *i* is painted with the raw value `i + 1` and the
  passed-in color is ignored.
- `render()` now clears the SDL renderer first
  (`SDL_SetRenderDrawColor(0, 0, 0, 255)` + `SDL_RenderClear`).
- `render()` calls `draw_rect(300, 200, 300, 150, 0xFFFF00FF)` between
  `draw_grid()` and `render_color_buffer()`.
- Trailing-newline fix at end of file (no behavior change).

## Run it

```
py -3.12 main.py                # 800x600 window (default)
py -3.12 main.py --fullscreen   # desktop-resolution borderless, like the C code
```

| Key | Action |
|-----|--------|
| ESC | Quit   |

Test hooks (CONVENTIONS.md §7): `RENDERER_MAX_FRAMES=<n>` exits after n
frames; `RENDERER_SAVE_FRAME=<path.png>` saves the final frame;
`SDL_VIDEODRIVER=dummy` runs headless.

## File map

| C file       | Python file | Notes |
|--------------|-------------|-------|
| `src/main.c` | `main.py`   | The whole step lives in one file, as in C. |

No `array.c`/`swap.c`/`upng.c` exist yet at this step, and there are no assets.

## Performance notes

- `clear_color_buffer`: full-buffer double loop → one broadcast assignment
  `color_buffer[:] = color`.
- `draw_grid`: modulo/step loop → one strided slice `color_buffer[::10, ::10]`.
- `draw_rect`: width x height double loop → one `np.arange` column ramp
  broadcast into a 2-D slice (bounds clamped to the screen; the C code has no
  clamp but its single call site fits on screen).

## Deviations (per CONVENTIONS.md §7 and §10)

- Windowed 800x600 by default; `--fullscreen` restores the C behavior.
- Input: the C code polls a single event per frame (laggy); the port drains
  the whole event queue each frame.
- Frame cap: the C step 7 loop is uncapped; the port adds the standard
  `clock.tick(60)` from the runtime contract.
- `render_color_buffer` converts the presented surface to drop per-pixel
  alpha, matching SDL's no-blending texture copy — this step's rect writes
  alpha-0 colors that must not become transparent.
