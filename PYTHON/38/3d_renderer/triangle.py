"""triangle.py — mirrors src/triangle.c.

Owns the ``face_t`` / ``triangle_t`` types and the two triangle drawing
routines (wireframe outline and flat-color fill).

Rasterization strategy (CONVENTIONS.md §5): the C code fills triangles by
sorting the vertices by y, splitting the triangle into a flat-bottom and a
flat-top half, and drawing one horizontal line per scanline. A per-pixel /
per-scanline Python loop would be far too slow, so ``draw_filled_triangle``
uses the vectorized **barycentric bounding-box rasterizer** instead:

1. Compute the triangle's screen-space bounding box, clipped to the window.
2. Evaluate the barycentric weights (alpha, beta, gamma) for *every* pixel
   in the box at once with NumPy broadcasting.
3. ``inside = (alpha >= 0) & (beta >= 0) & (gamma >= 0)`` selects the pixels
   covered by the triangle.
4. One fancy-indexed assignment stores the color for all covered pixels.

The result is visually identical to the C scanline fill, hundreds of times
faster than looping in Python.

The C helper ``int_swap`` is not ported: Python swaps with tuple assignment
(``a, b = b, a``), and the barycentric rasterizer needs no vertex sorting
at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from texture import tex2_t, texture_height, texture_width

import display


@dataclass
class face_t:
    """One triangular face: 1-based vertex indices, per-vertex UVs, base color."""

    a: int
    b: int
    c: int
    a_uv: tex2_t = field(default_factory=tex2_t)
    b_uv: tex2_t = field(default_factory=tex2_t)
    c_uv: tex2_t = field(default_factory=tex2_t)
    color: int = 0xFFFFFFFF


@dataclass
class triangle_t:
    """A projected screen-space triangle ready to be rasterized this frame."""

    points: np.ndarray = field(default_factory=lambda: np.zeros((3, 2)))  # 3 x (x, y)
    texcoords: list[tex2_t] = field(default_factory=lambda: [tex2_t(), tex2_t(), tex2_t()])
    color: int = 0xFFFFFFFF
    avg_depth: float = 0.0


###############################################################################
# Draw a filled triangle (flat color)
###############################################################################
#
#          (x0,y0)
#            / \
#           /   \
#          /     \
#         /       \
#        /         \
#   (x1,y1)---------\
#       \_           \
#          \_         \
#             \_       \
#                \_     \
#                   \    \
#                     \_  \
#                        \_\
#                           \
#                         (x2,y2)
#
###############################################################################
def draw_filled_triangle(
    x0: int, y0: int, x1: int, y1: int, x2: int, y2: int, color: int
) -> None:
    """Fill a triangle with a single flat color.

    Mirrors the C draw_filled_triangle (flat-top/flat-bottom scanline split),
    replaced by the vectorized barycentric bounding-box rasterizer described
    in the module docstring. The barycentric weights are winding-independent
    (numerator and denominator areas share the same sign), so triangles are
    filled correctly whichever way they face.
    """
    # C truncates the float screen coordinates through its `int` parameters.
    x0, y0, x1, y1, x2, y2 = int(x0), int(y0), int(x1), int(y1), int(x2), int(y2)

    # Step 1: clipped integer bounding box of the triangle.
    x_min = max(min(x0, x1, x2), 0)
    x_max = min(max(x0, x1, x2), display.window_width - 1)
    y_min = max(min(y0, y1, y2), 0)
    y_max = min(max(y0, y1, y2), display.window_height - 1)
    if x_min > x_max or y_min > y_max:
        return

    # Signed area of the parallelogram spanned by AC and AB. Zero means the
    # three points are collinear — nothing to fill.
    ac_x, ac_y = x2 - x0, y2 - y0
    ab_x, ab_y = x1 - x0, y1 - y0
    area_parallelogram_abc = ac_x * ab_y - ac_y * ab_x
    if area_parallelogram_abc == 0:
        return

    # Step 2: open pixel grid over the bounding box. Broadcasting a column of
    # y values against a row of x values gives 2-D results without
    # materializing a full meshgrid.
    pxs = np.arange(x_min, x_max + 1, dtype=np.float64)  # (nx,)
    pys = np.arange(y_min, y_max + 1, dtype=np.float64)[:, None]  # (ny, 1)

    # Vectors from/to the sample points.
    pc_x = x2 - pxs
    pc_y = y2 - pys
    pb_x = x1 - pxs
    pb_y = y1 - pys
    ap_x = pxs - x0
    ap_y = pys - y0

    # The three barycentric weights for every pixel at once:
    #   alpha = ||PC x PB|| / ||AC x AB||   (area opposite vertex A)
    #   beta  = ||AC x AP|| / ||AC x AB||   (area opposite vertex B)
    #   gamma = 1 - alpha - beta
    alpha = (pc_x * pb_y - pc_y * pb_x) / area_parallelogram_abc
    beta = (ac_x * ap_y - ac_y * ap_x) / area_parallelogram_abc
    gamma = 1.0 - alpha - beta

    # Step 3: a pixel is inside the triangle when all three weights are >= 0.
    inside = (alpha >= 0) & (beta >= 0) & (gamma >= 0)

    # Step 4: one fancy-indexed store into the color buffer.
    assert display.color_buffer is not None
    display.color_buffer[y_min : y_max + 1, x_min : x_max + 1][inside] = color


###############################################################################
# Draw a triangle using three raw line calls
###############################################################################
def draw_triangle(
    x0: int, y0: int, x1: int, y1: int, x2: int, y2: int, color: int
) -> None:
    """Draw the wireframe outline of a triangle."""
    x0, y0, x1, y1, x2, y2 = int(x0), int(y0), int(x1), int(y1), int(x2), int(y2)
    display.draw_line(x0, y0, x1, y1, color)
    display.draw_line(x1, y1, x2, y2, color)
    display.draw_line(x2, y2, x0, y0, color)


###############################################################################
# Draw a textured triangle based on a texture array of colors.
# We split the original triangle in two, half flat-bottom and half flat-top.
###############################################################################
def barycentric_weights(a: np.ndarray, b: np.ndarray, c: np.ndarray, p: np.ndarray) -> np.ndarray:
    """Return the barycentric weights (alpha, beta, gamma) of point p in triangle abc.

    Each weight is the ratio between the area of the sub-triangle opposite a
    vertex and the area of the whole triangle (areas via the 2D cross
    product). alpha + beta + gamma == 1 always, so gamma comes free.

    This scalar version mirrors the C function 1:1; the scanline filler
    below inlines the same math over a whole row of pixels at once.
    """
    ac = c - a
    ab = b - a
    ap = p - a
    pc = c - p
    pb = b - p

    # Area of the full parallelogram (twice the triangle abc) via 2D cross product
    area_parallelogram_abc = ac[0] * ab[1] - ac[1] * ab[0]  # || AC x AB ||

    alpha = (pc[0] * pb[1] - pc[1] * pb[0]) / area_parallelogram_abc
    beta = (ac[0] * ap[1] - ac[1] * ap[0]) / area_parallelogram_abc
    gamma = 1 - alpha - beta

    return np.array([alpha, beta, gamma], dtype=np.float64)


def _draw_texel_scanline(
    y: int, x_start: int, x_end: int,
    point_a: np.ndarray, point_b: np.ndarray, point_c: np.ndarray,
    u0: float, v0: float, u1: float, v1: float, u2: float, v2: float,
    texture: np.ndarray,
) -> None:
    """Texture one scanline [x_start, x_end) — the C draw_texel per-pixel call,
    vectorized across the whole row (CONVENTIONS.md §5).

    For every pixel of the row at once: compute the barycentric weights,
    interpolate u and v, map them into the texture, and store the texels
    with one fancy-indexed read + one slice write.
    """
    assert display.color_buffer is not None
    if y < 0 or y >= display.window_height:
        return
    x_start = max(x_start, 0)
    x_end = min(x_end, display.window_width)
    if x_start >= x_end:
        return

    # The row of pixel centers: p = (x, y) for x in [x_start, x_end)
    xs = np.arange(x_start, x_end, dtype=np.float64)

    # Vectors that do NOT depend on p (computed once per row)
    ac = point_c - point_a
    ab = point_b - point_a
    area_parallelogram_abc = ac[0] * ab[1] - ac[1] * ab[0]
    if area_parallelogram_abc == 0:
        return  # degenerate triangle

    # Vectors that DO depend on p, as arrays over the row
    pc_x = point_c[0] - xs
    pc_y = point_c[1] - y
    pb_x = point_b[0] - xs
    pb_y = point_b[1] - y
    ap_x = xs - point_a[0]
    ap_y = y - point_a[1]

    alpha = (pc_x * pb_y - pc_y * pb_x) / area_parallelogram_abc
    beta = (ac[0] * ap_y - ac[1] * ap_x) / area_parallelogram_abc
    gamma = 1.0 - alpha - beta

    # Perform the interpolation of all U and V values using barycentric weights
    interpolated_u = u0 * alpha + u1 * beta + u2 * gamma
    interpolated_v = v0 * alpha + v1 * beta + v2 * gamma

    # Map the UV coordinate to the full texture width and height.
    # C: abs((int)(u * texture_width)) with no upper clamp — an out-of-bounds
    # read waiting to happen at u == 1.0. Clamping to the last texel is the
    # safe equivalent (documented improvement, CONVENTIONS.md §10).
    tex_x = np.abs((interpolated_u * texture_width).astype(np.int32))
    tex_y = np.abs((interpolated_v * texture_height).astype(np.int32))
    np.clip(tex_x, 0, texture.shape[1] - 1, out=tex_x)
    np.clip(tex_y, 0, texture.shape[0] - 1, out=tex_y)

    display.color_buffer[y, x_start:x_end] = texture[tex_y, tex_x]


def draw_textured_triangle(
    x0: int, y0: int, u0: float, v0: float,
    x1: int, y1: int, u1: float, v1: float,
    x2: int, y2: int, u2: float, v2: float,
    texture: np.ndarray,
) -> None:
    """Rasterize a triangle with the flat-bottom/flat-top scanline split.

    Step 38 completes textured rasterization: the scanline walk from step 37
    stays, but every pixel now gets a real texel — its barycentric weights
    interpolate the three vertices' UVs, and the (u, v) result indexes into
    the texture.

    The C swaps with int_swap/float_swap from swap.c; Python tuple swaps do
    the same in one line each (CONVENTIONS.md §2).
    """
    # After the y-sort below, these are the triangle's screen points the
    # barycentric weights are measured against (C: point_a/b/c in draw_texel).

    x0, y0, x1, y1, x2, y2 = int(x0), int(y0), int(x1), int(y1), int(x2), int(y2)

    # We need to sort the vertices by y-coordinate ascending (y0 < y1 < y2)
    if y0 > y1:
        y0, y1 = y1, y0
        x0, x1 = x1, x0
        u0, u1 = u1, u0
        v0, v1 = v1, v0
    if y1 > y2:
        y1, y2 = y2, y1
        x1, x2 = x2, x1
        u1, u2 = u2, u1
        v1, v2 = v2, v1
    if y0 > y1:
        y0, y1 = y1, y0
        x0, x1 = x1, x0
        u0, u1 = u1, u0
        v0, v1 = v1, v0

    # Create vector points after we sort the vertices (C: point_a/b/c)
    point_a = np.array([x0, y0], dtype=np.float64)
    point_b = np.array([x1, y1], dtype=np.float64)
    point_c = np.array([x2, y2], dtype=np.float64)

    ###########################################################
    # Render the upper part of the triangle (flat-bottom)
    ###########################################################
    inv_slope_1 = (x1 - x0) / abs(y1 - y0) if y1 - y0 != 0 else 0.0
    inv_slope_2 = (x2 - x0) / abs(y2 - y0) if y2 - y0 != 0 else 0.0

    if y1 - y0 != 0:
        for y in range(y0, y1 + 1):
            x_start = int(x1 + (y - y1) * inv_slope_1)
            x_end = int(x0 + (y - y0) * inv_slope_2)
            if x_end < x_start:
                x_start, x_end = x_end, x_start  # swap if start is to the right of end
            _draw_texel_scanline(
                y, x_start, x_end,
                point_a, point_b, point_c,
                u0, v0, u1, v1, u2, v2,
                texture,
            )

    ###########################################################
    # Render the bottom part of the triangle (flat-top)
    ###########################################################
    inv_slope_1 = (x2 - x1) / abs(y2 - y1) if y2 - y1 != 0 else 0.0
    inv_slope_2 = (x2 - x0) / abs(y2 - y0) if y2 - y0 != 0 else 0.0

    if y2 - y1 != 0:
        for y in range(y1, y2 + 1):
            x_start = int(x1 + (y - y1) * inv_slope_1)
            x_end = int(x0 + (y - y0) * inv_slope_2)
            if x_end < x_start:
                x_start, x_end = x_end, x_start
            _draw_texel_scanline(
                y, x_start, x_end,
                point_a, point_b, point_c,
                u0, v0, u1, v1, u2, v2,
                texture,
            )
