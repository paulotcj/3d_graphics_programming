# Step 8 — A real solid draw_rect

This step cleans up step 7's drawing code so it does what it says: `draw_rect`
now fills the rectangle with the color passed in (step 7's version overwrote
the color argument with a per-column counter), and the dotted grid is dimmed
from white to gray. The result is the first intentional image of the course:
a gray 10-pixel dot grid with a solid magenta 300x150 rectangle at (300, 200).

## What changed vs step 7

Derived from the actual C diff (`7/3d_renderer/src/main.c` → `8/3d_renderer/src/main.c`):

- `draw_grid()`: dot color changed from white `0xFFFFFFFF` to gray `0xFFAAAAAA`.
- `draw_rect()`: removed the quirk that reset `color` to 0 and incremented it
  once per column — the function now fills every pixel with the `color`
  argument it receives, so the `0xFFFF00FF` rectangle finally shows up magenta.
- Removed the explanatory scan-order comments inside `draw_rect` (no behavior
  change).

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
- `draw_rect`: width x height double loop → one 2-D slice assignment (bounds
  clamped to the screen; the C code has no clamp but its single call site fits
  on screen).

## Deviations (per CONVENTIONS.md §7 and §10)

- Windowed 800x600 by default; `--fullscreen` restores the C behavior.
- Input: the C code polls a single event per frame (laggy); the port drains
  the whole event queue each frame.
- Frame cap: the C step 8 loop is uncapped; the port adds the standard
  `clock.tick(60)` from the runtime contract.
- `render_color_buffer` converts the presented surface to drop per-pixel
  alpha, matching SDL's no-blending texture copy.
