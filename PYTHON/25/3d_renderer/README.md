# Step 25 — Backface culling

Triangles facing away from the camera are skipped before projection. For
each face:

1. Build the edge vectors `AB = B − A` and `AC = C − A`.
2. **Cross product** `AB × AC` → the face normal (the clockwise winding in
   the mesh makes it point outward).
3. **Dot product** of the normal with the ray from the face to the camera.
4. Negative → the face looks away → `continue` (cull).

The wireframe stops being see-through: you only ever see the front of the
cube. Culling roughly halves the triangles drawn per frame — the first
"don't do work you can't see" optimization of the pipeline.

## What changed vs step 24

- `main.c` `update()` split into two phases: transform all 3 vertices first
  (now `z += 5`), run the culling test, then project only survivors.
- `camera_position` moved to the origin `{0, 0, 0}`.
- `setup()` loads `cube.obj` again (the demo vector code is removed).
- Rotation on all axes again (`x += 0.01, y += 0.01, z += 0.02`).
- `render()` no longer draws the yellow vertex markers.
- `vector.c`: formatting cleanup only.

## Run it

```
cd PYTHON/25/3d_renderer
py -3.12 main.py               # 800x600 window
py -3.12 main.py --fullscreen  # borderless desktop-resolution, like the C
```

`ESC` or closing the window quits. Watch the cube spin — back faces never
draw.

## File map

| C file          | Python file   | Notes                             |
|-----------------|---------------|------------------------------------|
| `main.c`        | `main.py`     | + backface culling in update()    |
| `vector.c/.h`   | `vector.py`   | cross/dot now earning their keep  |
| `display.c/.h`  | `display.py`  | unchanged                         |
| `mesh.c/.h`     | `mesh.py`     | unchanged                         |
| `triangle.c/.h` | `triangle.py` | unchanged                         |
| `array.c/.h`    | —             | Python `list`                     |
| `Makefile`      | —             | nothing to compile                |

## Performance notes

Culling is per-face scalar math (mirrors the C exactly); per-pixel work
stays vectorized (CONVENTIONS.md §5). Runs at the 60 FPS cap.
