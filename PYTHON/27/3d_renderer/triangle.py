"""triangle.py — mirrors src/triangle.c (step 27).

Owns the ``face_t`` / ``triangle_t`` types and the NEW routine of this step:
``draw_filled_triangle``, the classic flat-top/flat-bottom rasterizer.

The C version sorts the three vertices by y, splits the triangle at the
middle vertex into a flat-bottom half and a flat-top half, and fills each
half one horizontal scanline at a time by walking two edge slopes.

Rasterization strategy (CONVENTIONS.md §5): the C code fills each scanline
by calling ``draw_line(x_start, y, x_end, y)`` — a per-pixel DDA loop. Here
each scanline becomes ONE NumPy slice assignment
(``color_buffer[y, x_left:x_right + 1] = color``), which paints exactly the
same pixels: a horizontal DDA from x_start to x_end visits every integer x
between them, inclusive. The remaining Python loop is per-*scanline* (at
most window_height iterations), never per-pixel.

C's ``int_swap`` helper is not ported — Python tuple assignment
(``a, b = b, a``) does the same job.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

import display


@dataclass
class face_t:
    """One triangular face of a mesh: 1-based indices into the vertex list."""

    a: int
    b: int
    c: int


@dataclass
class triangle_t:
    """A screen-space triangle ready to be rasterized this frame (3 x (x, y))."""

    points: np.ndarray = field(default_factory=lambda: np.zeros((3, 2)))


def _draw_scanline(x_start: int, x_end: int, y: int, color: int) -> None:
    """Fill one horizontal scanline [x_start, x_end] inclusive.

    Replaces the C call ``draw_line(x_start, y, x_end, y, color)`` with a
    single clipped slice assignment — same pixels, no per-pixel loop.
    """
    if y < 0 or y >= display.window_height:
        return
    left = max(min(x_start, x_end), 0)
    right = min(max(x_start, x_end), display.window_width - 1)
    if left > right:
        return
    assert display.color_buffer is not None
    display.color_buffer[y, left : right + 1] = color


###############################################################################
# Draw a filled triangle with a flat bottom
###############################################################################
#
#        (x0,y0)
#          / \
#         /   \
#        /     \
#       /       \
#      /         \
#  (x1,y1)------(x2,y2)
#
###############################################################################
def fill_flat_bottom_triangle(
    x0: int, y0: int, x1: int, y1: int, x2: int, y2: int, color: int
) -> None:
    """Fill scanlines from the top vertex down to the flat bottom edge."""
    # Find the two slopes (two triangle legs). Guard the degenerate
    # zero-height case (all three y equal) that C leaves as a division by
    # zero — with a 0 slope the single scanline drawn matches C's output.
    inv_slope_1 = (x1 - x0) / (y1 - y0) if y1 != y0 else 0.0
    inv_slope_2 = (x2 - x0) / (y2 - y0) if y2 != y0 else 0.0

    # Start x_start and x_end from the top vertex (x0,y0)
    x_start = float(x0)
    x_end = float(x0)

    # Loop all the scanlines from top to bottom
    for y in range(y0, y2 + 1):
        # C passes the float x's into draw_line's int parameters, which
        # truncates toward zero — int() does the same.
        _draw_scanline(int(x_start), int(x_end), y, color)
        x_start += inv_slope_1
        x_end += inv_slope_2


###############################################################################
# Draw a filled triangle with a flat top
###############################################################################
#
#  (x0,y0)------(x1,y1)
#      \         /
#       \       /
#        \     /
#         \   /
#          \ /
#        (x2,y2)
#
###############################################################################
def fill_flat_top_triangle(
    x0: int, y0: int, x1: int, y1: int, x2: int, y2: int, color: int
) -> None:
    """Fill scanlines from the bottom vertex up to the flat top edge."""
    # Find the two slopes (two triangle legs)
    inv_slope_1 = (x2 - x0) / (y2 - y0) if y2 != y0 else 0.0
    inv_slope_2 = (x2 - x1) / (y2 - y1) if y2 != y1 else 0.0

    # Start x_start and x_end from the bottom vertex (x2,y2)
    x_start = float(x2)
    x_end = float(x2)

    # Loop all the scanlines from bottom to top
    for y in range(y2, y0 - 1, -1):
        _draw_scanline(int(x_start), int(x_end), y, color)
        x_start -= inv_slope_1
        x_end -= inv_slope_2


###############################################################################
# Draw a filled triangle with the flat-top/flat-bottom method
# We split the original triangle in two, half flat-bottom and half flat-top
###############################################################################
#
#          (x0,y0)
#            / \
#           /   \
#          /     \
#         /       \
#        /         \
#   (x1,y1)------(Mx,My)
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
    """Sort vertices by y, split at the middle vertex, fill both halves."""
    x0, y0, x1, y1, x2, y2 = int(x0), int(y0), int(x1), int(y1), int(x2), int(y2)

    # We need to sort the vertices by y-coordinate ascending (y0 < y1 < y2)
    if y0 > y1:
        y0, y1 = y1, y0
        x0, x1 = x1, x0
    if y1 > y2:
        y1, y2 = y2, y1
        x1, x2 = x2, x1
    # because we swapped y1 above we need to compare it again
    if y0 > y1:
        y0, y1 = y1, y0
        x0, x1 = x1, x0

    if y1 == y2:
        # Draw flat-bottom triangle
        fill_flat_bottom_triangle(x0, y0, x1, y1, x2, y2, color)
    elif y0 == y1:
        # Draw flat-top triangle
        fill_flat_top_triangle(x0, y0, x1, y1, x2, y2, color)
    else:
        # Calculate the new vertex (Mx,My) using triangle similarity.
        # C uses integer division, which truncates toward zero — int()
        # reproduces that exactly (Python's // would floor instead).
        my = y1
        mx = int((x2 - x0) * (y1 - y0) / (y2 - y0)) + x0

        # Draw flat-bottom triangle
        fill_flat_bottom_triangle(x0, y0, x1, y1, mx, my, color)

        # Draw flat-top triangle
        fill_flat_top_triangle(x1, y1, mx, my, x2, y2, color)
