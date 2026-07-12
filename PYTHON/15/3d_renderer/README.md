# Step 15 — Rotating the point cloud

The first animated 3D transform of the course. The 9x9x9 cloud of points
introduced in the earlier steps now spins: a rotation angle grows a little
every frame and each point is rotated around the x, y, and z axes before
being perspective-projected and drawn as a small yellow rectangle. This step
introduces `vec3_rotate_x/y/z`, derived from the angle-addition identities.

## What changed vs step 14

Derived from the actual C diff (`14/3d_renderer/src` → `15/3d_renderer/src`):

- `main.c`: new global `vec3_t cube_rotation = {0, 0, 0}`.
- `main.c` `update()`: increments `cube_rotation.x/y/z` by `0.01` each frame,
  rotates every point with `vec3_rotate_x`, then `vec3_rotate_y`, then
  `vec3_rotate_z`, and translates/projects the *transformed* point instead of
  the raw one.
- `vector.c`: previously a `// TODO` stub — now implements `vec3_rotate_x`,
  `vec3_rotate_y`, and `vec3_rotate_z` from the angle-addition identities
  (`cos(a+b) = cos a cos b - sin a sin b`, `sin(a+b) = sin a cos b + cos a sin b`).
  Note this step's `vec3_rotate_y` uses the same sign pattern as the z
  rotation (`x*cos - z*sin` / `x*sin + z*cos`); the course revisits the sign
  convention in a later step, and the Python mirrors *this* step's math.
- `vector.h`: declares the three rotation functions.

`display.c` is unchanged from step 14.

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

| C file                  | Python file  | Notes                                            |
|-------------------------|--------------|--------------------------------------------------|
| `src/main.c`            | `main.py`    | setup, project, update (now rotating), render    |
| `src/display.c/.h`      | `display.py` | window, color buffer, grid/pixel/rect drawing    |
| `src/vector.c/.h`       | `vector.py`  | `vec3_rotate_x/y/z` — new in this step           |

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
- The C step has **no frame cap** (it was added later in the course); the
  Python loop caps at 60 FPS with `clock.tick(60)` so the rotation speed is
  machine-independent, per the conventions' runtime contract.
- `np.linspace(-1, 1, 9)` replaces the C `for (float x = -1; x <= 1; x += 0.25)`
  loop, avoiding float-accumulation drift while producing the same 9 values.
