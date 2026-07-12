# 3D Graphics Programming — Python Edition

A complete Python mirror of the 59-step C course in this repository, which
builds a **software 3D renderer from scratch** — no OpenGL, no GPU: every
pixel is computed by the program itself, from plotting a single dot all the
way to a textured, camera-driven, frustum-clipped 3D scene.

Each numbered folder here mirrors the same-numbered C folder at the repo root.
The programs behave the same, the file names match (`display.c` → `display.py`),
and the function names match — you can read the C and Python side by side.
What changed is *how* the pixels get computed: every per-pixel C loop became a
vectorized NumPy operation, which is what makes a software rasterizer viable
in Python at interactive frame rates.

> **New here? Start with three documents:**
> 1. This file — what the project is and how to run it.
> 2. [CONVENTIONS.md](CONVENTIONS.md) — how the C code maps to Python and the
>    performance playbook every step uses.
> 3. Any step's `README.md` — what that step adds and how it works.

## Requirements & setup

- Python 3.10+ (developed on 3.12)
- Two libraries: **pygame** (window/input — SDL2, the same library the C uses)
  and **numpy** (all buffers and rasterization math)

```
py -3.12 -m pip install -r requirements.txt
```

## Running any step

```
cd PYTHON/<step>/3d_renderer
py -3.12 main.py
```

- `ESC` quits. Later steps add render-mode keys (`1`–`6`), culling toggles
  (`c`/`x`), and camera controls (`W`/`S`, arrow keys) — each step's README
  lists exactly what it supports.
- Default is an 800×600 window (the C used a borderless fullscreen window;
  windowed is friendlier for development). Steps that support it accept
  `--fullscreen`.

### Test hooks (used by the automated verification, handy for you too)

Every graphical step honors three environment variables:

| Variable | Effect |
|---|---|
| `RENDERER_MAX_FRAMES=n` | exit cleanly after *n* frames |
| `RENDERER_SAVE_FRAME=path.png` | save the final frame to a PNG on exit |
| `SDL_VIDEODRIVER=dummy` | run without any window (headless) |

## ⚠️ About the missing `.obj` models

The original repo ships only PNG **textures** — the `.obj` **mesh files** the
C code references from step 22 onward (`cube.obj`, `f22.obj`, `efa.obj`,
`f117.obj`, `crab.obj`, `drone.obj`, `runway.obj`) were never committed, so
those C steps cannot actually load their models as published.

The Python mirror handles this gracefully:

- `assets/cube.obj` is **generated** (from the cube hard-coded in the C's
  `mesh.c`), so the OBJ parser is genuinely exercised.
- Any other missing `.obj` prints a one-line warning and **falls back to the
  built-in cube**, textured with that model's own PNG — every step runs out
  of the box.
- Drop the original course `.obj` files into a step's `assets/` folder and
  they load exactly as in C.

## The journey — step by step

| Step | Introduces |
|---|---|
| [1](1/3d_renderer/) | Hello World: Project Starting Point |
| [2](2/3d_renderer/) | SDL window and game loop |
| [3](3/3d_renderer/) | Color buffer and SDL texture |
| [4](4/3d_renderer/) | Querying display mode for fullscreen sizing |
| [5](5/3d_renderer/) | Drawing a grid in the color buffer |
| [6](6/3d_renderer/) | Dotted grid via loop stride |
| [7](7/3d_renderer/) | Drawing rectangles in the color buffer |
| [8](8/3d_renderer/) | Cleaning up rectangle and grid drawing |
| [9](9/3d_renderer/) | Splitting code into display module |
| [10](10/3d_renderer/) | Vectors and a 3D point cloud cube |
| [11](11/3d_renderer/) | Orthographic projection with FOV scaling |
| [12](12/3d_renderer/) | Perspective projection (divide by z) |
| [13](13/3d_renderer/) | No code changes (lecture-only step) |
| [14](14/3d_renderer/) | No code changes (lecture-only step) |
| [15](15/3d_renderer/) | Vector rotation (trigonometric rotation transforms) |
| [16](16/3d_renderer/) | Fixed frame rate with FPS capping |
| [17](17/3d_renderer/) | Frame rate capping with SDL_Delay |
| [18](18/3d_renderer/) | Triangle meshes: vertices and faces |
| [19](19/3d_renderer/) | Line drawing (DDA) and wireframe triangles |
| [20](20/3d_renderer/) | Dynamic arrays for triangles to render |
| [21](21/3d_renderer/) | Dynamic mesh struct with dynamic arrays |
| [22](22/3d_renderer/) | Loading OBJ files |
| [23](23/3d_renderer/) | Loading a complex OBJ model (F-22) |
| [24](24/3d_renderer/) | Vector math operations (add, sub, dot, cross) |
| [25](25/3d_renderer/) | Backface culling |
| [26](26/3d_renderer/) | Vector normalization |
| [27](27/3d_renderer/) | Filled triangle rasterization (flat-top/flat-bottom) |
| [28](28/3d_renderer/) | Interactive render modes and culling toggles |
| [29](29/3d_renderer/) | Painter's algorithm depth sorting |
| [30](30/3d_renderer/) | 4x4 matrices and matrix scale transform |
| [31](31/3d_renderer/) | Translation matrix |
| [32](32/3d_renderer/) | Rotation matrices |
| [33](33/3d_renderer/) | Matrix-matrix multiplication and the world matrix |
| [34](34/3d_renderer/) | Perspective projection matrix |
| [35](35/3d_renderer/) | Flat shading with directional light |
| [36](36/3d_renderer/) | Texture setup: UV coordinates and texture pipeline |
| [37](37/3d_renderer/) | Textured triangle scanline fill (flat-top/flat-bottom) |
| [38](38/3d_renderer/) | Barycentric coordinates for texture mapping |
| [39](39/3d_renderer/) | Perspective-correct texture mapping |
| [40](40/3d_renderer/) | Fixing inverted UV texture coordinates |
| [41](41/3d_renderer/) | Loading PNG textures with uPNG |
| [42](42/3d_renderer/) | Loading UV texture coordinates from OBJ files |
| [43](43/3d_renderer/) | Textured OBJ model loading (crab mesh) |
| [44](44/3d_renderer/) | Z-buffer for per-pixel depth testing |
| [45](45/3d_renderer/) | Z-buffered filled triangles replace painter's algorithm |
| [46](46/3d_renderer/) | Camera and look-at view matrix |
| [47](47/3d_renderer/) | Delta-time based frame-rate independent animation |
| [48](48/3d_renderer/) | Keyboard-controlled FPS camera movement |
| [49](49/3d_renderer/) | Frustum planes for clipping |
| [50](50/3d_renderer/) | Polygon clipping data structures and pipeline |
| [51](51/3d_renderer/) | Sutherland-Hodgman polygon clipping against planes |
| [52](52/3d_renderer/) | Triangulating clipped polygons (fan triangulation) |
| [53](53/3d_renderer/) | Separate horizontal and vertical FOV clipping |
| [54](54/3d_renderer/) | Clipping texture coordinates (UV interpolation) |
| [55](55/3d_renderer/) | Encapsulating display state behind accessor functions |
| [56](56/3d_renderer/) | Encapsulating the global light (getter/setter API) |
| [57](57/3d_renderer/) | Multiple meshes with per-mesh textures |
| [58](58/3d_renderer/) | Code refactor: graphics pipeline stages function |
| [59](59/3d_renderer/) | Full-resolution fullscreen rendering |

Each step folder's README explains the change in detail and how to see it on screen.

## How the conversion stays fast

The C renderer touches every pixel in nested loops. Python can't afford that,
so each step applies the same playbook (full details in
[CONVENTIONS.md](CONVENTIONS.md) §5):

- The color buffer is one `numpy uint32` array holding the same `0xAARRGGBB`
  values as the C buffer, blitted to the screen once per frame.
- Clears, grids, and rectangles are array slices; lines are `np.linspace`.
- Filled and textured triangles use a **barycentric bounding-box rasterizer**:
  the weights for *all* pixels in a triangle's bounding box are computed in a
  few array operations, then one boolean mask does the inside test, the
  z-buffer test, and the store.
- Mesh vertices are transformed by **one matrix multiplication per mesh per
  frame** instead of vertex-by-vertex.

## Files that intentionally have no Python counterpart

| C file | Why it's gone |
|---|---|
| `upng.c` / `upng.h` (1,281 lines) | PNG decoding is one `pygame.image.load()` call |
| `array.c` / `array.h` | C needed a hand-rolled dynamic array; Python has `list` |
| `swap.c` / `swap.h` | `a, b = b, a` |
| `Makefile` | nothing to compile — `py -3.12 main.py` |

## Repo map

| Folder | Contents |
|---|---|
| `1/` … `59/` | one folder per course step, each self-contained |
| `test/` | the tiny multi-file "hello" toolchain check |
| `working/` | identical to step 59 (as in the C original) |
| `CONVENTIONS.md` | the conversion rules and performance playbook |
| `requirements.txt` | pygame + numpy |
