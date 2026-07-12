# Step 1 — Hello World (toolchain sanity check)

The starting point of the 3D software renderer. This step contains no
graphics at all: it is a console program that prints `Hello World!` and
exits. In the C course it existed to prove the compiler, Makefile, and run
workflow before adding SDL; the Python version plays the same role for the
Python interpreter.

## What changed vs step 0

There is no step 0 — this is the first step, the starting point of the
whole series. It establishes:

- `main.c` → `main.py` with a single `main()` that prints `Hello World!`.
- The build/run workflow (C: `make && ./renderer`; Python: `python main.py`).

## Run it

```
python main.py
```

Prints `Hello World!` and exits with status 0. No window, no controls.

Note: the runtime contract env hooks (`RENDERER_MAX_FRAMES`,
`RENDERER_SAVE_FRAME`) do not apply here — there is no window or frame loop
yet. They start at the first SDL/pygame step.

## File map

| C file       | Python file | Notes                                    |
|--------------|-------------|------------------------------------------|
| `src/main.c` | `main.py`   | Direct 1:1 port of the `printf` program. |
| `Makefile`   | —           | Not needed; Python has no compile step.  |

## Performance notes

Nothing to optimize — no rendering, no per-pixel work, no dependencies
(neither pygame nor numpy is imported in this step).
