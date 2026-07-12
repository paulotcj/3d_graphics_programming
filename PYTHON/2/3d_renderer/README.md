# Step 2 — First SDL window and game loop

The first graphical step: it opens an 800x600 window and spins the classic
game loop — `process_input()`, `update()`, `render()` — until the user quits.
Rendering is nothing more than clearing the screen to solid red through the
SDL renderer and presenting it; there is no CPU-side color buffer yet.

## What changed vs step 1

Derived from the actual C diff (`src/main.c` is the only changed file):

- Added `<stdbool.h>` and `<SDL2/SDL.h>` includes and three globals:
  `is_running`, `SDL_Window* window`, `SDL_Renderer* renderer`.
- Added `initialize_window()`: `SDL_Init(SDL_INIT_EVERYTHING)`, an 800x600
  centered **borderless** `SDL_CreateWindow`, and `SDL_CreateRenderer`,
  each with an error message on failure.
- Added empty `setup()` and `update()` stubs (both `// TODO:`).
- Added `process_input()`: polls one SDL event and stops the loop on
  `SDL_QUIT` or the ESC key.
- Added `render()`: `SDL_SetRenderDrawColor(renderer, 255, 0, 0, 255)` +
  `SDL_RenderClear` + `SDL_RenderPresent` — a solid red screen.
- `main()` no longer prints `Hello World!`; it now runs
  `initialize_window()`, `setup()`, then the
  `while (is_running) { process_input(); update(); render(); }` loop.

## Run it

```
python main.py
```

| Control          | Action |
|------------------|--------|
| ESC or close box | Quit   |

Test hooks (start at this step, per CONVENTIONS.md §7):

- `RENDERER_MAX_FRAMES=<n>` — exit cleanly after n frames.
- `RENDERER_SAVE_FRAME=<path.png>` — save the final frame to a PNG on exit.
- Works headless with `SDL_VIDEODRIVER=dummy`.

## File map

| C file       | Python file | Notes                                                          |
|--------------|-------------|----------------------------------------------------------------|
| `src/main.c` | `main.py`   | 1:1 port — same function names, same loop, same red clear.     |
| `Makefile`   | —           | Not needed; Python has no compile step.                        |

## Deviations / improvements (per CONVENTIONS.md §7 and §10)

- **Framed window instead of borderless**: the C window uses
  `SDL_WINDOW_BORDERLESS`; the Python default is a normal 800x600 framed
  window, which is friendlier for development. Size and rendering are
  identical.
- **Full event drain**: the C code calls `SDL_PollEvent` once per frame,
  which lags when events queue up; the port drains the whole queue each
  frame (`pygame.event.get()`).
- No frame cap, matching the C code — SDL_Delay/FPS capping arrives in a
  later step.

## Performance notes

Nothing to optimize yet: no per-pixel work exists in this step (the red
clear is a single `Surface.fill`, i.e. SDL's own clear). numpy is not
imported; it enters with the CPU-side color buffer in a later step.
