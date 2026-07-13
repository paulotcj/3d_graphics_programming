# Step 37 — Textured triangle scanline fill (flat-top/flat-bottom)

`draw_textured_triangle` gets its body: sort the three vertices by y, then
walk the scanlines of the **flat-bottom** upper half and the **flat-top**
lower half, computing each row's left/right x bounds from the edges'
inverse slopes. The pixels are filled with a magenta checkerboard
placeholder — real texel sampling arrives in step 38.

## What changed vs step 36

- `triangle.c`: the scanline walk implemented (vertex y-sort with
  `int_swap`/`float_swap`, inverse-slope stepping, per-row fill).
- `main.c`: comment cleanup only.

## The Python version

- The C's `int_swap`/`float_swap` (from `swap.c`) become tuple swaps:
  `y0, y1 = y1, y0` (CONVENTIONS.md §2).
- The per-row fill is one numpy slice write plus a stride-2 slice for the
  even-x magenta pixels — the row loop remains (it mirrors the C's scanline
  structure), but no per-pixel Python loop exists (CONVENTIONS.md §5).

## Run it

```
cd PYTHON/37/3d_renderer
py -3.12 main.py
```

Keys `1`–`6` switch render modes (default: textured + wire), `c`/`d`
culling, `ESC` quit. Expect the magenta-checker cube.

## Performance notes

Scanline count ≈ triangle height (≤ a few hundred rows); each row is O(1)
numpy calls. 60 FPS cap holds comfortably.
