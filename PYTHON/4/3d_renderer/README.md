# Step 4 — Full-screen window from the desktop display mode

This step makes one small quality-of-life change to the renderer shell: the
window is no longer hard-coded to 800x600. The C code asks SDL for the
current desktop display mode and sizes its borderless window to fill the
whole screen. Everything else — the CPU-side color buffer streamed to the
screen and cleared to solid yellow each frame — is unchanged from step 3.

## What changed vs step 3

Derived from the actual C diff (`src/main.c` is the only changed file):

- `initialize_window()` now declares an `SDL_DisplayMode display_mode`,
  calls `SDL_GetCurrentDisplayMode(0, &display_mode)` (display index 0),
  and overwrites `window_width = display_mode.w` /
  `window_height = display_mode.h` before `SDL_CreateWindow` — so the
  borderless window fills the desktop resolution instead of 800x600.
- That is the entire diff; no other function changed.

## Run it

```
python main.py               # 800x600 framed window (default, see below)
python main.py --fullscreen  # C behavior: desktop-resolution borderless window
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

The C `SDL_Texture* color_buffer_texture` has no Python counterpart: pygame
builds a Surface directly from the buffer's bytes each frame
(`pygame.image.frombuffer(..., "BGRA")`, CONVENTIONS.md §4), so no separate
streaming texture object is needed.

## Deviations / improvements (per CONVENTIONS.md §7 and §10)

- **Windowed default, `--fullscreen` opt-in**: the C step uses the
  desktop-resolution borderless trick; per CONVENTIONS.md §7 the Python
  default stays a normal 800x600 framed window (friendlier for
  development), and `--fullscreen` reproduces the C behavior — the desktop
  size is read via `pygame.display.Info()` (pygame's
  `SDL_GetCurrentDisplayMode`) and the window is created borderless
  (`pygame.NOFRAME`). The rendering logic is unaffected either way.
- **Full event drain**: the C code calls `SDL_PollEvent` once per frame,
  which lags when events queue up; the port drains the whole queue each
  frame (`pygame.event.get()`).
- **Zero-initialized buffer**: C's `malloc` leaves the buffer uninitialized,
  so the C first frame shows garbage memory; `np.zeros` makes the first
  frame black. Every frame after that is identical (solid yellow).
- No frame cap, matching the C code — SDL_Delay/FPS capping arrives in a
  later step.

## Performance notes

- `color_buffer` is a numpy `uint32` array of shape `(height, width)`
  holding the exact C `0xAARRGGBB` literals (CONVENTIONS.md §4).
- `clear_color_buffer()` — the C double loop over all pixels — is a single
  broadcast assignment: `color_buffer[:] = color` (CONVENTIONS.md §5). No
  per-pixel Python loop anywhere.
- Presentation is one `pygame.image.frombuffer(buffer.tobytes(), (w, h),
  "BGRA")` + blit — little-endian ARGB bytes are exactly BGRA order.
