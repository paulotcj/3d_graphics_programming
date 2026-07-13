# Step 31 — Translation matrix

The homogeneous-coordinates payoff. `matrix.py` gains
`mat4_make_translation`, which stores the x/y/z offsets in the matrix's
**last column**:

```
| 1 0 0 tx |   | x |   | x + tx·w |
| 0 1 0 ty | · | y | = | y + ty·w |
| 0 0 1 tz |   | z |   | z + tz·w |
| 0 0 0  1 |   | w |   |    w     |
```

Because vertices carry w = 1 (set in `vec4_from_vec3`), the multiplication
*moves* the point — something a 3×3 matrix can never do. The hard-coded
`transformed_vertex.z += 5` camera push is deleted; translation is now
expressed like every other transform.

## What changed vs step 30

- `matrix.c`/`matrix.h`: new `mat4_make_translation(tx, ty, tz)`.
- `main.c` `update()`: scale/rotation animation commented out; instead
  `mesh.translation.x += 0.01` and `mesh.translation.z = 5.0`; the vertex
  loop applies scale then translation matrices.

On screen: the (no longer spinning) cube slides steadily to the right.

## Run it

```
cd PYTHON/31/3d_renderer
py -3.12 main.py
```

Keys: `1`–`4` render modes, `c`/`d` culling, `ESC` quit.

## File map

Same as step 30, with `matrix.py` one function richer.

## Performance notes

Unchanged — matrix ops are numpy `@` products; per-pixel work vectorized
(CONVENTIONS.md §5); 60 FPS cap.
