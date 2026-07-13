# Step 42 — Loading UV coordinates from OBJ files

The OBJ loader learns texture coordinates: `vt u v` lines are parsed into a
list, and each face's UV indices (the middle number of `f v/vt/vn`) look up
the real per-vertex UVs. Any textured OBJ model now carries its own mapping.

## What changed vs step 41

- `mesh.c` loader: parses `vt` lines; faces reference `texcoords[vt - 1]`.
- `main.c`: loads `cube.obj` + `cube.png` from disk (the parser is now the
  real path, not the hard-coded cube).
- `triangle.c`: flips V (`v = 1 - v`) — texture V grows down, OBJ V grows up.
- `free_resources` drops `upng_free` (the PNG lives for the program's life).

## Run it

```
cd PYTHON/42/3d_renderer
py -3.12 main.py
```

Press **H** in the window for the full key list (on-screen help). `ESC`
quits.

## Performance notes

All per-pixel work is vectorized numpy (CONVENTIONS.md §5): barycentric
bounding-box rasterization, masked z-buffer tests, fancy-indexed texture
sampling, batched vertex transforms. Runs at the 60 FPS cap.
