# Step 17 — SDL_Delay instead of busy-wait

The spinning 9x9x9 point cloud from step 16, with a better frame-rate cap.
Step 16 held 60 FPS by busy-waiting — spinning a `while` loop (and a whole
CPU core) until `FRAME_TARGET_TIME` milliseconds had passed. This step
computes how many milliseconds are left until the target frame time and
sleeps for exactly that long with `SDL_Delay`, yielding the CPU to the OS.

## What changed vs step 16

Derived from the actual C diff (`16/3d_renderer/src` → `17/3d_renderer/src`):

- `main.c` `update()`: the busy-wait
  `while (!SDL_TICKS_PASSED(SDL_GetTicks(), previous_frame_time + FRAME_TARGET_TIME));`
  is replaced with:
  - `int time_to_wait = FRAME_TARGET_TIME - (SDL_GetTicks() - previous_frame_time);`
  - `if (time_to_wait > 0 && time_to_wait <= FRAME_TARGET_TIME) SDL_Delay(time_to_wait);`
  — only delaying when the frame ran too fast, with a sanity check that the
  wait never exceeds one full frame period.

`display.c` and `vector.c` are unchanged from step 16 — this is the only
change.

In the Python conversion the code is unchanged too: `clock.tick(display.FPS)`
at the top of `update()` already sleeps (rather than spins) until the 60 FPS
target — which is precisely the behavior the C code adopts in this step. What
was documented in step 16 as an improvement over the C busy-wait is now a 1:1
match; only the comments/docstrings were updated to mirror the new C code.

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
| `src/main.c`            | `main.py`    | setup, project, update (SDL_Delay-style pacing), render |
| `src/display.c/.h`      | `display.py` | window, color buffer, drawing, `FPS`/`FRAME_TARGET_TIME` — unchanged |
| `src/vector.c/.h`       | `vector.py`  | `vec3_rotate_x/y/z` — unchanged                        |

There is no `assets/` folder at this step (no meshes or textures yet).

## Performance notes

- `clear_color_buffer` → single array fill `buffer[:] = color`.
- `draw_grid` (dot every 10 px) → one strided slice `buffer[::10, ::10]`.
- `draw_rect` → one clipped 2-D slice assignment per rectangle.
- The 729-point rotate/project loop keeps the scalar `vec3_rotate_*` helpers
  for 1:1 traceability with the C code the step teaches — at 729 points it is
  not a hot path and comfortably holds 60 FPS.

Documented deviations/improvements (CONVENTIONS.md §7/§10):

- Windowed 800x600 by default; `--fullscreen` restores the C borderless
  desktop-resolution behavior.
- The event loop drains the whole queue (`pygame.event.get()`) instead of the
  C code's single `SDL_PollEvent` per frame, fixing the classic input lag.
- `pygame.time.Clock.tick(60)` sleeps to the frame target, matching the C
  code's new `SDL_Delay` pacing (no longer a deviation as of this step).
- `np.linspace(-1, 1, 9)` replaces the C `for (float x = -1; x <= 1; x += 0.25)`
  loop, avoiding float-accumulation drift while producing the same 9 values.
