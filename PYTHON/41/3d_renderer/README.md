# Step 41 — Loading PNG textures (uPNG in C, one line in Python)

The hard-coded red-brick array is gone — `setup()` loads
`./assets/cube.png` from disk. In C this took bundling the **1,281-line
uPNG decoder** (`upng.c`) and switching the SDL window texture to RGBA32 to
match its byte order. In Python the entire step is one `pygame.image.load`
call (see `texture.py`) whose output already lands in our buffer's ARGB
convention — so the C's window-format switch needs no mirror; the on-screen
result is identical.

## What changed vs step 40

- New `upng.c`/`upng.h` in C — **never ported** (CONVENTIONS.md §2).
- `texture.c`: `load_png_texture_data(filename)` fills `mesh_texture` and
  the texture dimensions from the file.
- `main.c`: default render mode becomes filled; SDL texture format →
  RGBA32; the vertex-marker literal `0xFF0000FF` now shows RED in the C —
  mirrored as `0xFFFF0000` in our ARGB pipeline (same on-screen color).

## Run it

```
cd PYTHON/41/3d_renderer
py -3.12 main.py
```

Press **H** in the window for the full key list (on-screen help). `ESC`
quits.

## Performance notes

All per-pixel work is vectorized numpy (CONVENTIONS.md §5): barycentric
bounding-box rasterization, masked z-buffer tests, fancy-indexed texture
sampling, batched vertex transforms. Runs at the 60 FPS cap.
