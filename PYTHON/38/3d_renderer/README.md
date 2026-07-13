# Step 38 — Barycentric coordinates for texture mapping

The checkerboard is gone: every pixel now gets a real texel. For a pixel P
inside triangle ABC, the **barycentric weights** (α, β, γ) measure how close
P sits to each vertex — each weight is the area of the sub-triangle opposite
that vertex divided by the whole triangle's area (areas via the 2D cross
product), and they always sum to 1. Interpolating the vertex UVs with those
weights gives the pixel's (u, v), which indexes the red-brick texture.

This is **affine** texture mapping: correct for the flat-on cube face, but
it will visibly warp once perspective foreshortens a triangle — the fix
(interpolating with 1/w) is step 39.

## What changed vs step 37

- `triangle.c`: new `barycentric_weights(a, b, c, p)` and `draw_texel(...)`;
  the scanline loops call `draw_texel` per pixel instead of the checker.

## The Python version

`triangle.py` keeps the scalar `barycentric_weights` (1:1 with the C, for
side-by-side reading) but the scanline filler inlines the same math **over a
whole row of pixels at once**: α/β/γ become numpy arrays, u/v interpolate as
arrays, and one fancy-indexed read (`texture[tex_y, tex_x]`) plus one slice
write stores every texel of the row (CONVENTIONS.md §5).

One safety improvement (CONVENTIONS.md §10): the C maps UVs with
`abs((int)(u * texture_width))` and no upper clamp — at u = 1.0 that reads
out of bounds. The Python clamps to the last texel.

## Run it

```
cd PYTHON/38/3d_renderer
py -3.12 main.py
```

Keys `1`–`6` render modes, `c`/`d` culling, `ESC` quit. Expect a spinning
red-brick cube.

## Performance notes

Per row: ~10 numpy array ops regardless of width. The 60 FPS cap holds.
