# Python Conversion Conventions

This document is the **single source of truth** for how the C programs in this
repository are converted to Python. Every converted step follows these rules so
that all 59 steps (plus `test` and `working`) read as one coherent, evolving
codebase — exactly like the C original, but idiomatic, fast, and documented.

---

## 1. Goals (in priority order)

1. **Same observable behavior** as the C step it mirrors — same window, same
   drawing, same controls, same animation.
2. **Fast.** Software rasterization in pure Python is ~100× too slow, so every
   per-pixel loop from the C code is re-expressed as a **NumPy array
   operation**. Target: 60 FPS on the untextured steps, interactive frame
   rates (20+ FPS) on the fully textured, multi-mesh final steps.
3. **Readable by a junior developer.** Every module has a docstring explaining
   *what it does and why it exists*; every non-obvious algorithm has a short
   explanation with the math written out; names are spelled out in full.
4. **1:1 traceability to the C code.** Same file names, same function names
   (snake_case, as in C), same call structure, so a reader can put the C and
   Python versions side by side.

## 2. Technology stack

| Concern            | C original                  | Python conversion                         |
|--------------------|-----------------------------|-------------------------------------------|
| Window / input     | SDL2                        | **pygame 2** (SDL2 under the hood)        |
| Color buffer       | `uint32_t*` heap array      | **NumPy** `uint32` array, shape `(h, w)`  |
| Z-buffer           | `float*` heap array         | NumPy `float32` array, shape `(h, w)`     |
| Dynamic arrays     | `array.c` (custom)          | Python `list` (no port needed — document) |
| PNG decoding       | `upng.c` (1,281 lines)      | `pygame.image.load()` (one line)          |
| `swap.c`           | swap helpers                | tuple swap `a, b = b, a` (no port needed) |

Dependencies: **only `pygame` and `numpy`**. Python ≥ 3.10 with type hints.

## 3. Directory mirror

```
PYTHON/<step>/3d_renderer/
    main.py           # mirrors src/main.c   — game loop, pipeline stages
    display.py        # mirrors src/display.c — window, buffers, drawing
    vector.py         # mirrors src/vector.c  — vec2/vec3/vec4 math
    matrix.py         # mirrors src/matrix.c  — 4×4 matrices
    mesh.py           # mirrors src/mesh.c    — mesh data + OBJ loading
    triangle.py       # mirrors src/triangle.c
    light.py, camera.py, clipping.py, texture.py  # same pattern
    assets/           # copied from the C step's assets folder (+ cube.obj, see §8)
    README.md         # per-step documentation (see §9)
```

- A step only contains the modules its C counterpart has (step 5 has just
  `main.py`; step 59 has all of them).
- `array.c/h`, `swap.c/h`, and `upng.c/h` are **never ported** — each step's
  README notes what replaced them.
- `PYTHON/test/` mirrors the little `test/` C program (main + helper module).
- `PYTHON/working/` mirrors `working/` (identical content to step 59).

## 4. The pixel format trick (keep C color literals working)

The C code uses `SDL_PIXELFORMAT_ARGB8888` and colors like `0xFF888888`
(`0xAARRGGBB`). The Python conversion keeps the **same uint32 literals**:

- `color_buffer` is `np.ndarray[uint32]` of shape `(height, width)`, holding
  `0xAARRGGBB` values — identical to the C buffer.
- To present it, view the buffer as raw bytes and hand it to pygame as BGRA
  (little-endian ARGB == BGRA byte order):

```python
surface = pygame.image.frombuffer(color_buffer.tobytes(), (w, h), "BGRA")
```

  (or blit via `pygame.surfarray` after a documented channel shuffle — pick
  ONE approach in `display.py` and reuse it everywhere.)

## 5. Performance playbook (apply everywhere; document each use)

Every C per-pixel loop maps to a specific NumPy idiom:

| C loop                                   | NumPy replacement                                         |
|------------------------------------------|-----------------------------------------------------------|
| `clear_color_buffer` double loop         | `buffer[:] = color`                                        |
| `draw_grid` modulo loop                  | slicing: `buffer[::10, :] = c; buffer[:, ::10] = c`        |
| `draw_rect` double loop                  | 2-D slice assignment with clipping to screen bounds        |
| DDA / Bresenham `draw_line`              | `np.linspace` both axes → round → `buffer[ys, xs] = color` |
| flat-top/flat-bottom scanline fill       | per-scanline slice fill **or** barycentric bounding-box    |
| textured/z-buffered per-pixel loop       | **barycentric bounding-box rasterizer** (see below)        |
| z-buffer compare per pixel               | boolean mask: `mask = w_interp > zbuf[ys, xs]` then fancy-index assignment |
| texture sample per pixel                 | fancy indexing: `texels[tex_y_idx, tex_x_idx]`             |

**Barycentric bounding-box rasterizer** (the core trick for filled/textured
triangles, replacing the C scanline code from the z-buffer steps onward):

1. Compute the triangle's clipped integer bounding box.
2. Build the pixel grid once: `xs, ys = np.meshgrid(...)` (or open grids).
3. Compute the three edge functions / barycentric weights for *all* pixels in
   the box at once (pure array arithmetic).
4. `inside = (alpha >= 0) & (beta >= 0) & (gamma >= 0)`.
5. Perspective-correct interpolation of `1/w`, `u/w`, `v/w` as array math.
6. Z-test with a mask, then one fancy-indexed store into the color buffer and
   z-buffer.

This preserves *exactly* the same visual result as the C scanline code while
being hundreds of times faster than a Python per-pixel loop. Each step's
README must include a short "Performance notes" section naming the tricks used.

Additional rules:

- Transform **all vertices of a mesh in one matmul** per frame
  (`vertices @ world_matrix.T`), then gather per-face — instead of C's
  per-face-per-vertex multiply. Document this as a deliberate improvement.
- Never allocate buffers inside the frame loop when avoidable; reuse
  preallocated arrays.
- Keep scalar helper functions (e.g. `vec3_cross`) for readability where they
  are *not* hot; hot paths use NumPy directly with a comment pointing back to
  the helper it replaces.

## 6. Structure and naming

- Function names mirror the C names: `initialize_window` / `init_window`,
  `process_input`, `update`, `render`, `draw_filled_triangle`, … exactly as in
  the step's C code (each step uses whatever names its C code uses).
- C global variables become **module-level state in the matching module**
  (e.g. `display.py` owns `color_buffer`, `window_width`) — mirroring how the
  C code uses translation-unit globals. Where the later C steps encapsulate
  state behind getters (`get_window_width()`), mirror those getters.
- Vectors/matrices: use small NumPy arrays (`np.array([x, y, z],
  dtype=np.float64)`) as the underlying representation, with `vector.py` /
  `matrix.py` providing the C-named constructors and operations
  (`vec3_new`, `vec3_cross`, `mat4_make_perspective`, …). `triangle_t`,
  `face_t`, `mesh_t`, etc. become `@dataclass` classes with the same field
  names.
- Type hints on every function signature. Docstrings: one-line summary +
  explanation where the algorithm is non-trivial. Module docstring at top of
  every file stating what it mirrors and what it owns.
- No abbreviations the C code doesn't use. No cleverness that hides control
  flow. `if __name__ == "__main__": main()` in every `main.py`.

## 7. Runtime contract (every step MUST honor this — used by automated tests)

- Runnable with `python main.py` from inside the step's `3d_renderer/` folder
  (use paths relative to `__file__`, NOT the current working directory, for
  assets).
- **Window**: default 800×600 centered window. If the C step used the
  desktop-resolution borderless trick, support `--fullscreen` to opt in, and
  note the deviation in the README (a windowed default is friendlier for
  development; the rendering logic is unaffected).
- **Frame cap**: same as C — `FPS = 60`, implemented with
  `clock.tick(FPS)`; `delta_time` in seconds from the clock, clamped to a
  sane max (0.05 s) to avoid physics jumps on stalls (document as an
  improvement).
- **Controls**: exactly the step's C controls (ESC quit, 1–6 render modes,
  c/x culling, WASD/arrows camera, … as applicable to the step).
- **Test hooks** (three environment variables, implemented in every step):
  - `RENDERER_MAX_FRAMES=<n>` — exit cleanly after n frames.
  - `RENDERER_SAVE_FRAME=<path.png>` — save the final rendered frame to a PNG
    on exit (via `pygame.image.save` of the presented surface).
  - Respect `SDL_VIDEODRIVER=dummy` (works automatically with pygame; do not
    call anything that requires a real display — guard `pygame.display.Info`
    usage accordingly).
  These hooks live in a tiny, clearly-commented block and are identical in
  every step.

## 8. Missing assets — graceful fallback (IMPORTANT)

The original repository ships **only PNG textures**; the `.obj` mesh files the
C code references (`cube.obj`, `f22.obj`, `efa.obj`, `f117.obj`, `crab.obj`,
`drone.obj`, `runway.obj`) were never committed, so C steps ≥ 22 cannot
actually load their meshes as-is.

The Python conversion fixes this without changing behavior when assets exist:

1. `load_obj_file_data(path)` (and the later `load_mesh(...)`): if the file is
   missing, print a clear one-line warning and **fall back to the built-in
   cube mesh** (the same hard-coded 8-vertex/12-face cube from `mesh.c`,
   including its UVs at the texture steps), using `cube.png` as the fallback
   texture when a texture is expected.
2. `cube.obj` is not shipped either — when referenced, the loader takes the
   same fallback path to the hard-coded cube data, which is identical
   geometry.
3. Every affected README documents: "drop the original course `.obj` files
   into `assets/` to see the real models."
4. **The real course models ARE shipped**: the actual `.obj` meshes
   (cube, f22, f117, efa, crab, runway) live in each referencing step's
   `assets/` folder and load through the OBJ parser. The missing-file
   fallback above remains as a safety net if an asset is ever removed. (The
   root `.gitignore` has a `!**/assets/*.obj` exception so these meshes are
   not swallowed by the compiler-object-file `*.obj` rule.)

The OBJ parser must support the exact subset the C parser supports for that
step (`v`, `vt`, `f v/vt/vn` — check the step's `mesh.c`).

## 9. Per-step README.md (required, ~1 page)

```markdown
# Step <n> — <short title, e.g. "Perspective projection">
<2–4 sentences: what this step demonstrates in the 3D-engine journey.>

## What changed vs step <n-1>
<bullet list derived from the actual C diff — the real changes, not guesses.>

## Run it
<commands, controls table if applicable>

## File map
<C file → Python file table, including "not ported because ..." rows>

## Performance notes
<which NumPy tricks this step uses>
```

Steps with no C change vs the previous step (e.g. 13, 14) say so explicitly.

## 10. What "improved" means (and what it does NOT mean)

Allowed improvements (each documented in the README where applied):
- NumPy vectorization; batched vertex transforms; buffer reuse.
- Asset-missing fallback (§8); windowed default (§7); delta-time clamp (§7).
- Bug fixes present in the C code (e.g. the classic single-`SDL_PollEvent`
  input lag before the C code switched to a `while`-poll — fix it, note it).
- Type hints, docstrings, constants instead of magic numbers.

NOT allowed:
- Changing the rendering algorithm the step teaches (e.g. don't replace the
  painter's-algorithm sort with a z-buffer before the step where the C code
  does).
- Skipping features, controls, or visual details of the step.
- Adding dependencies beyond pygame + numpy.
- Restructuring the module layout away from the C file mirror.
