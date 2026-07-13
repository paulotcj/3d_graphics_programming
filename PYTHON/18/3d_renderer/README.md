# Step 18 — Triangle meshes: vertices and faces

The point cloud is replaced by real **geometry**. A mesh is two lists: the
cube's 8 corner vertices, and 12 faces that reference them by 1-based index
(two triangles per cube side — the same convention `.obj` files use). Each
frame every face's three vertices are rotated, translated away from the
camera, perspective-projected, and their screen positions marked with small
yellow squares. The connecting wireframe lines arrive in step 19.

## What changed vs step 17

- New `mesh.c`/`mesh.h` → [mesh.py](mesh.py): `mesh_vertices` (8) and
  `mesh_faces` (12, clockwise winding).
- New `triangle.c`/`triangle.h` → [triangle.py](triangle.py): `face_t`
  (vertex indexes) and `triangle_t` (projected screen points).
- `main.c`: the 729-point arrays are gone; `update()` now loops faces →
  vertices, and the center-of-screen offset moved from `render()` into
  `update()`; `render()` draws three 3×3 rects per triangle.

## Run it

```
cd PYTHON/18/3d_renderer
py -3.12 main.py               # 800x600 window
py -3.12 main.py --fullscreen  # borderless desktop-resolution, like the C
```

`ESC` or closing the window quits. You should see the 8 cube corners spinning
(each corner drawn once per face that uses it).

## File map

| C file          | Python file   | Notes                                |
|-----------------|---------------|---------------------------------------|
| `main.c`        | `main.py`     | game loop, face transform + project  |
| `display.c/.h`  | `display.py`  | window, buffer, drawing helpers      |
| `vector.c/.h`   | `vector.py`   | vec2/vec3 + rotation functions       |
| `mesh.c/.h`     | `mesh.py`     | hard-coded cube vertices + faces     |
| `triangle.c/.h` | `triangle.py` | `face_t`, `triangle_t` dataclasses   |
| `Makefile`      | —             | nothing to compile                   |

## Performance notes

12 faces × 3 vertices per frame — trivially fast; the loop mirrors the C
1:1. All pixel operations remain the vectorized numpy routines in
`display.py` (CONVENTIONS.md §5). Runs at the 60 FPS cap.
