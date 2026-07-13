# Step 26 — Vector normalization

Same culled wireframe cube as step 25, refined: `vector.py` gains
`vec2_normalize` / `vec3_normalize` — **in-place** functions, mirroring the
C versions that take a `vec2_t*` / `vec3_t*` pointer — and the backface
culling code now normalizes the edge vectors and the face normal.

For a pure sign test (`dot < 0`) the normal's length never mattered, only
its direction — but normalized vectors are about to matter a lot: lighting
(step 35) compares angles via dot products, which only works cleanly on
unit vectors. The habit starts here.

## What changed vs step 25

- `vector.c`/`vector.h`: new `vec2_normalize(vec2_t*)` and
  `vec3_normalize(vec3_t*)`.
- `main.c` culling block: `vec3_normalize(&vector_ab)`,
  `vec3_normalize(&vector_ac)`, `vec3_normalize(&normal)`.
- Rest of the diff is whitespace cleanup.

## Run it

```
cd PYTHON/26/3d_renderer
py -3.12 main.py               # 800x600 window
py -3.12 main.py --fullscreen  # borderless desktop-resolution, like the C
```

`ESC` or closing the window quits.

## File map

| C file          | Python file   | Notes                            |
|-----------------|---------------|-----------------------------------|
| `main.c`        | `main.py`     | culling now uses unit vectors    |
| `vector.c/.h`   | `vector.py`   | + in-place normalize functions   |
| others          | unchanged     | see step 25                      |

## Performance notes

Unchanged from step 25 — 60 FPS cap. Note the Python normalize mutates the
numpy array in place, exactly matching the C pointer semantics, so call
sites read identically in both languages.
