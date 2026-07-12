# Step 3 — CPU-side color buffer

This step introduces the core idea of the whole course: a CPU-side **color
buffer** — one `uint32` per pixel in ARGB8888 format — that the program fills
itself and then hands to SDL to display. From here on, "rendering" means
writing pixels into this array; SDL only delivers it to the screen. The
visible result is a solid yellow (`0xFFFFFF00`) screen.

## What changed vs step 2

Derived from the actual C diff (`src/main.c` is the only changed file):

- New globals: `uint32_t* color_buffer`, `SDL_Texture* color_buffer_texture`,
  and `window_width` / `window_height` (800x600) replacing the hard-coded
  `SDL_CreateWindow` size literals.
- `setup()` is no longer a TODO: it mallocs the color buffer
  (`window_width * window_height` uint32s) and creates a streaming
  `SDL_PIXELFORMAT_ARGB8888` texture for it.
- New `render_color_buffer()`: `SDL_UpdateTexture` (pitch =
  `window_width * sizeof(uint32_t)`) + `SDL_RenderCopy`.
- New `clear_color_buffer(uint32_t color)`: double loop writing `color` into
  every pixel of the buffer.
- `render()` now clears the backbuffer to **black** (was red), copies the
  color buffer to the screen, then clears the color buffer to yellow
  `0xFFFFFF00` for the next frame, and presents.
- New `destroy_window()`: `free(color_buffer)`, `SDL_DestroyRenderer`,
  `SDL_DestroyWindow`, `SDL_Quit` — called by `main()` after the loop.
- Minor whitespace/brace formatting touch-ups.

## Run it

```
python main.py
```

| Control          | Action |
|------------------|--------|
| ESC or close box | Quit   |

Test hooks (per CONVENTIONS.md §7):

- `RENDERER_MAX_FRAMES=<n>` — exit cleanly after n frames.
- `RENDERER_SAVE_FRAME=<path.png>` — save the final frame to a PNG on exit.
- Works headless with `SDL_VIDEODRIVER=dummy`.

## File map

| C file       | Python file | Notes                                                              |
|--------------|-------------|--------------------------------------------------------------------|
| `src/main.c` | `main.py`   | 1:1 port — same function names, same render order, same colors.   |
| `Makefile`   | —           | Not needed; Python has no compile step.                            |

## Deviations / improvements (per CONVENTIONS.md §7 and §10)

- **Framed window instead of borderless**: the C window uses
  `SDL_WINDOW_BORDERLESS`; the Python default is a normal 800x600 framed
  window, which is friendlier for development. Size and rendering are
  identical.
- **Full event drain**: the C code calls `SDL_PollEvent` once per frame,
  which lags when events queue up; the port drains the whole queue each
  frame (`pygame.event.get()`).
- **Zero-initialized buffer**: C's `malloc` leaves the buffer uninitialized,
  so the C program's first frame is undefined garbage; numpy zero-fills, so
  the first frame here is black. Every frame after that is identical
  (solid yellow).
- No frame cap, matching the C code — SDL_Delay/FPS capping arrives in a
  later step.

## Performance notes

First use of the CONVENTIONS.md §5 playbook:

- `clear_color_buffer` — the C double loop over 480,000 pixels becomes a
  single numpy broadcast fill: `color_buffer[:] = color`.
- Presentation (CONVENTIONS.md §4) — the `(height, width)` uint32
  `0xAARRGGBB` buffer is viewed as raw bytes and wrapped with
  `pygame.image.frombuffer(..., "BGRA")` (little-endian ARGB == BGRA byte
  order), replacing `SDL_UpdateTexture` + `SDL_RenderCopy`. The C color
  literals are kept unchanged.
