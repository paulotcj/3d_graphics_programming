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

from texture import tex2_t

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
def _fill_checker_scanline(y: int, x_start: int, x_end: int) -> None:
    """Fill one scanline [x_start, x_end) with the step-37 placeholder pattern.

    C: per pixel, ``(x % 2 == 0 && y % 2 == 0) ? 0xFFFF00FF : 0x00000000``.
    NumPy: fill the row slice with the zero color, then hit the even-x
    positions with magenta using a stride-2 slice (CONVENTIONS.md §5) —
    no per-pixel Python loop.
    """
    assert display.color_buffer is not None
    if y < 0 or y >= display.window_height:
        return
    x_start = max(x_start, 0)
    x_end = min(x_end, display.window_width)
    if x_start >= x_end:
        return

    row = display.color_buffer[y, x_start:x_end]
    row[:] = 0x00000000
    if y % 2 == 0:
        first_even = x_start if x_start % 2 == 0 else x_start + 1
        row[first_even - x_start :: 2] = 0xFFFF00FF


def draw_textured_triangle(
    x0: int, y0: int, u0: float, v0: float,
    x1: int, y1: int, u1: float, v1: float,
    x2: int, y2: int, u2: float, v2: float,
    texture: np.ndarray,
) -> None:
    """Rasterize a triangle with the flat-bottom/flat-top scanline split.

    Step 37 implements the *shape* of textured rasterization: sort the
    vertices by y, walk the scanlines of the upper (flat-bottom) half and
    then the lower (flat-top) half, computing the left/right x bounds from
    the edge inverse-slopes. The pixels are filled with a placeholder
    checkerboard — actual texel sampling arrives in step 38.

    The C swaps with int_swap/float_swap from swap.c; Python tuple swaps do
    the same in one line each (CONVENTIONS.md §2).
    """
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
            _fill_checker_scanline(y, x_start, x_end)

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
            _fill_checker_scanline(y, x_start, x_end)
