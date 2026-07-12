# Step 9 — Splitting out display.c

This step is a pure refactor with zero visual change: the window/renderer
globals and all drawing helpers move out of `main.c` into a new
`display.c`/`display.h` pair, leaving `main.c` with just the game loop. The
image is identical to step 8: a gray 10-pixel dot grid with a solid magenta
300x150 rectangle at (300, 200).

## What changed vs step 8

Derived from the actual C diff (`8/3d_renderer/src` → `9/3d_renderer/src`):

- New files `display.c` and `display.h`. Moved into them, unchanged in
  behavior: the globals `window`, `renderer`, `color_buffer`,
  `color_buffer_texture`, `window_width`, `window_height`, and the functions
  `initialize_window`, `draw_grid`, `draw_rect`, `render_color_buffer`,
  `clear_color_buffer`, `destroy_window`.
- `main.c` now `#include "display.h"` and keeps only `is_running`, `setup`
  (which still allocates the buffer/texture declared in display.h),
  `process_input`, `update`, `render`, and `main`.
- No drawing or behavior change of any kind.

The Python port mirrors the split: the same functions and globals move from
`main.py` into a new `display.py`; `main.py`'s `setup()` still allocates
`display.color_buffer`, exactly like main.c assigning the `extern` buffer.

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

| C file          | Python file  | Notes |
|-----------------|--------------|-------|
| `src/main.c`    | `main.py`    | Game loop only, as in C. |
| `src/display.c` | `display.py` | Window, color buffer, drawing helpers. |
| `src/display.h` | —            | Not needed — Python imports replace the header. |

No `array.c`/`swap.c`/`upng.c` exist yet at this step, and there are no assets.

## Performance notes

Unchanged from step 8 (the C change is a pure file split):

- `clear_color_buffer`: full-buffer double loop → one broadcast assignment
  `color_buffer[:] = color`.
- `draw_grid`: modulo/step loop → one strided slice `color_buffer[::10, ::10]`.
- `draw_rect`: width x height double loop → one 2-D slice assignment (bounds
  clamped to the screen; the C code has no clamp but its single call site fits
  on screen).

## Deviations (per CONVENTIONS.md §7 and §10)

- Windowed 800x600 by default; `--fullscreen` restores the C behavior.
- Input: the C code polls a single event per frame (laggy); the port drains
  the whole event queue each frame.
- Frame cap: the C step 9 loop is uncapped; the port adds the standard
  `clock.tick(60)` from the runtime contract.
- `render_color_buffer` converts the presented surface to drop per-pixel
  alpha, matching SDL's no-blending texture copy.
