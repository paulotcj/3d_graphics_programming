# Step 32 — Rotation matrices

The last of the three basic transforms becomes a matrix. `matrix.py` gains
`mat4_make_rotation_x/y/z` — cos/sin placed on the two axes that mix, the
third axis untouched:

```
X: | 1  0  0  0 |   Y: |  c  0  s  0 |   Z: | c -s  0  0 |
   | 0  c -s  0 |      |  0  1  0  0 |      | s  c  0  0 |
   | 0  s  c  0 |      | -s  0  c  0 |      | 0  0  1  0 |
   | 0  0  0  1 |      |  0  0  0  1 |      | 0  0  0  1 |
```

Note Y's flipped sign pattern — that's what keeps all three rotating the
same (counter-clockwise) direction in the left-handed coordinate system
(see `docs/3D Rotation Direction and Handedness.pdf` next to the C step).

## What changed vs step 31

- `matrix.c`/`matrix.h`: the three rotation matrix constructors.
- `main.c` `update()`: builds all five matrices, applies them per vertex in
  the order **scale → rotate x → y → z → translate**; animation is now a
  steady y-axis spin at fixed depth z = 5.
- `vector.c`: the old `vec3_rotate_y` helper's signs corrected to match the
  matrix convention (mirrored in `vector.py`).

## Run it

```
cd PYTHON/32/3d_renderer
py -3.12 main.py
```

Keys: `1`–`4` render modes, `c`/`d` culling, `ESC` quit.

## File map

Same as step 31, with `matrix.py` three functions richer.

## Performance notes

Unchanged — numpy `@` products per vertex, vectorized pixels
(CONVENTIONS.md §5), 60 FPS cap.
