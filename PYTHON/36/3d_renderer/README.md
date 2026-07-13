# Step 36 — Texture setup: UV coordinates and the texture pipeline

The plumbing for texture mapping. Nothing textured appears on screen yet —
by design (the C leaves `draw_textured_triangle` as a TODO stub) — but every
piece of data a texture needs now flows through the pipeline:

- `texture.py` (new, mirroring `texture.c`): the `tex2_t` UV type, the
  64×64 texture dimensions, and the global `mesh_texture`.
- Every cube face carries **per-vertex UVs** (`a_uv`, `b_uv`, `c_uv`).
- `triangle_t` carries the projected triangle's `texcoords` to the renderer.
- Two new render modes: key `5` textured, key `6` textured + wire (the new
  default).

## The red-brick texture

The C embeds the texture as a 16,384-byte `REDBRICK_TEXTURE[]` array pasted
into `texture.c`. Rather than transcribe that wall of hex, those exact bytes
were exported once to [assets/redbrick.png](assets/redbrick.png)
(pixel-identical) and `texture.py` loads them back into a numpy `uint32`
ARGB array at startup (CONVENTIONS.md §2). Same texels, sane storage.

## What changed vs step 35

- New `texture.c/.h` → `texture.py`; new `swap.c/.h` (int/float swap
  helpers — never ported: Python swaps with `a, b = b, a`).
- `display.h`: `RENDER_TEXTURED`, `RENDER_TEXTURED_WIRE`; keys 5/6.
- `mesh.c`: cube faces gain UVs; `main.c` loads the cube + assigns
  `mesh_texture`; rotation slows to 0.003; vertex-dot color literal changes
  to `0xFF0000FF`.
- `triangle.c`: `draw_textured_triangle(...)` — **a TODO stub until
  step 37**; `face_t`/`triangle_t` gain UV fields.

## Run it

```
cd PYTHON/36/3d_renderer
py -3.12 main.py
```

Keys: `1`–`6` render modes (5/6 draw only wire until step 37), `c`/`d`
culling, `ESC` quit.

## Performance notes

No new hot path this step (the textured rasterizer is a stub). Texture
loading produces a `(64, 64) uint32` ARGB array — the same layout as the
color buffer, so texels can be stored with zero conversion later.
