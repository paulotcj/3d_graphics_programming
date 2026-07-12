# Step 16 — Fixed frame rate

The spinning 9x9x9 point cloud from step 15 gets a fixed 60 FPS frame cap.
Until now the loop ran as fast as the machine allowed, so the rotation speed
depended on the hardware; this step introduces the classic
`FPS` / `FRAME_TARGET_TIME` constants and waits at the top of `update()`
until the target frame time has elapsed, making the animation speed
machine-independent.

## What changed vs step 15

Derived from the actual C diff (`15/3d_renderer/src` → `16/3d_renderer/src`):

- `display.h`: new `#define FPS 60` and
  `#define FRAME_TARGET_TIME (1000 / FPS)` (≈16 ms per frame).
- `main.c`: new global `int previous_frame_time = 0`.
- `main.c` `update()`: starts with a busy-wait —
  `while (!SDL_TICKS_PASSED(SDL_GetTicks(), previous_frame_time + FRAME_TARGET_TIME));`
  — then stores `previous_frame_time = SDL_GetTicks()`, so each frame takes
  at least `FRAME_TARGET_TIME` milliseconds.

Everything else (`display.c`, `vector.c/.h`, the rotate/project/render code)
is unchanged from step 15.

## Run it

```sh
py -3.12 main.py                # 800x600 window (default)
py -3.12 main.py --fullscreen   # borderless desktop-resolution, like the C code
```

Requires `pygame` and `numpy` (`py -3.12 -m pip install pygame numpy`).

| Key | Action |
|-----|--------|
| ESC | Quit   |

Test hooks (CONVENTIONS.md §7): `RENDERER_MAX_FRAMES=<n>` exits after n
frames; `RENDERER_SAVE_FRAME=<path.png>` saves the final frame on exit;
`SDL_VIDEODRIVER=dummy` runs headless.

## File map

| C file                  | Python file  | Notes                                                  |
|-------------------------|--------------|--------------------------------------------------------|
| `src/main.c`            | `main.py`    | setup, project, update (now frame-capped), render      |
| `src/display.c/.h`      | `display.py` | window, color buffer, drawing; new `FPS`/`FRAME_TARGET_TIME` |
| `src/vector.c/.h`       | `vector.py`  | `vec3_rotate_x/y/z` (unchanged)                        |

There is no `assets/` folder at this step (no meshes or textures yet).

## Performance notes

- `clear_color_buffer` → single array fill `buffer[:] = color`.
- `draw_grid` (dot every 10 px) → one strided slice `buffer[::10, ::10]`.
- `draw_rect` → one clipped 2-D slice assignment per rectangle.
- The 729-point rotate/project loop keeps the scalar `vec3_rotate_*` helpers
  for 1:1 traceability with the C code the step teaches — at 729 points it is
  not a hot path and comfortably holds 60 FPS.

Documented deviations/improvements (CONVENTIONS.md §7/§10):

- The C busy-wait (`while (!SDL_TICKS_PASSED(...));`) spins a CPU core at
  100%; `pygame.time.Clock.tick(FPS)` at the top of `update()` enforces the
  same ≥16 ms frame time by sleeping instead, so no `previous_frame_time`
  bookkeeping is needed. `FPS` and `FRAME_TARGET_TIME` live in `display.py`,
  mirroring the new `display.h` defines.
- Windowed 800x600 by default; `--fullscreen` restores the C borderless
  desktop-resolution behavior.
- The event loop drains the whole queue (`pygame.event.get()`) instead of the
  C code's single `SDL_PollEvent` per frame, fixing the classic input lag.
- `np.linspace(-1, 1, 9)` replaces the C `for (float x = -1; x <= 1; x += 0.25)`
  loop, avoiding float-accumulation drift while producing the same 9 values.
