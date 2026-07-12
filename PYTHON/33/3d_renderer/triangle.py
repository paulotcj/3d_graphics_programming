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

import display


@dataclass
class face_t:
    """One triangular face of a mesh: 1-based vertex indices + base color."""

    a: int
    b: int
    c: int
    color: int = 0xFFFFFFFF


@dataclass
class triangle_t:
    """A projected screen-space triangle ready to be rasterized this frame."""

    points: np.ndarray = field(default_factory=lambda: np.zeros((3, 2)))  # 3 x (x, y)
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
