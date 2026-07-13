# Step 30 — 4×4 matrices and the matrix scale transform

The renderer switches from per-axis trigonometry helpers to **matrices**. A
new `matrix.py` (mirroring `matrix.c`) introduces `mat4_t` with three
functions: `mat4_identity`, `mat4_make_scale`, and `mat4_mul_vec4`. Vertices
are promoted to four components — `vec4_from_vec3` sets **w = 1**, the
homogeneous-coordinates trick that will let a single matrix also carry
*translation* (next step).

In this step only the scale matrix is applied. The rotation angles keep
accumulating but are no longer used in the transform, and `mesh.scale` grows
a little every frame — so the cube stops spinning and visibly **inflates**,
x slightly faster than y.

## What changed vs step 29

- New `matrix.c`/`matrix.h` → [matrix.py](matrix.py).
- `vector.c`/`vector.h`: new `vec4_t` type plus `vec4_from_vec3` /
  `vec3_from_vec4` conversions.
- `mesh.h`: `mesh_t` gains `scale` (initialized `{1,1,1}`) and
  `translation` (`{0,0,0}`).
- `main.c` `update()`: scale factors animated (`+0.002` / `+0.001`), the
  rotate calls replaced by `mat4_mul_vec4(scale_matrix, vertex)`, culling
  and projection now convert vec4 → vec3 where needed.

## Run it

```
cd PYTHON/30/3d_renderer
py -3.12 main.py               # 800x600 window
py -3.12 main.py --fullscreen  # borderless desktop-resolution, like the C
```

Keys: `1` wireframe+dots, `2` wireframe, `3` filled, `4` filled+wire,
`c` cull on, `d` cull off, `ESC` quit.

## File map

| C file          | Python file   | Notes                                 |
|-----------------|---------------|----------------------------------------|
| `matrix.c/.h`   | `matrix.py`   | **new**: mat4 identity/scale/mul-vec  |
| `vector.c/.h`   | `vector.py`   | + vec4 and conversions                |
| `mesh.c/.h`     | `mesh.py`     | + scale/translation fields            |
| `main.c`        | `main.py`     | scale-matrix transform                |
| others          | unchanged     |                                        |

## Performance notes

`mat4_mul_vec4` is `m @ v` — NumPy's matrix product, one call instead of the
C's 16 multiplies spelled out. Per-pixel work stays vectorized
(CONVENTIONS.md §5). Runs at the 60 FPS cap.
