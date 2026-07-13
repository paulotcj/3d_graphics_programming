"""triangle.py — mirrors src/triangle.c.

Owns the ``face_t`` / ``triangle_t`` types, the barycentric-weights math,
and the three triangle drawing routines (wireframe outline, flat-color fill,
and — the point of this step — **perspective-correct** textured fill).

Rasterization strategy (CONVENTIONS.md §5): the C code fills triangles by
sorting the vertices by y, splitting the triangle into a flat-bottom and a
flat-top half, and looping pixel by pixel (calling ``draw_texel`` once per
pixel for textures). A per-pixel Python loop would be ~100x too slow, so
both filled and textured triangles use the vectorized **barycentric
bounding-box rasterizer** instead:

1. Compute the triangle's screen-space bounding box, clipped to the window.
2. Evaluate the barycentric weights (alpha, beta, gamma) for *every* pixel
   in the box at once with NumPy broadcasting — the exact same formula the
   C ``barycentric_weights`` uses, just on arrays.
3. ``inside = (alpha >= 0) & (beta >= 0) & (gamma >= 0)`` selects the pixels
   covered by the triangle.
4. Interpolate ``u/w``, ``v/w``, and ``1/w`` as array math, sample the
   texture with fancy indexing, and store with one masked assignment.

The result is visually identical to the C scanline fill, hundreds of times
faster than looping in Python. The C per-pixel helper ``draw_texel`` is
folded into ``draw_textured_triangle`` (steps 4-5 above); the scalar
``barycentric_weights`` is kept below for 1:1 readability with the C file.

Why interpolate 1/w and u/w instead of w and u? Perspective projection is
not linear in screen space — a texture point halfway across a triangle on
screen is NOT halfway across it in 3D. But 1/w and u/w *are* linear in
screen space, so we interpolate those and recover u = (u/w) / (1/w) per
pixel. That is what "perspective-correct texture mapping" means, and it is
exactly what this step adds over step 38's affine (distorted) mapping.

The C helpers ``int_swap`` / ``float_swap`` (swap.c) are not ported: the
barycentric rasterizer needs no vertex sorting at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

import display
import texture as texture_module
from texture import tex2_t
from vector import Vec2, Vec3, vec2_sub


@dataclass
class face_t:
    """One triangular face of a mesh: 1-based vertex indices + UVs + base color."""

    a: int
    b: int
    c: int
    a_uv: tex2_t
    b_uv: tex2_t
    c_uv: tex2_t
    color: int


@dataclass
class triangle_t:
    """A projected screen-space triangle ready to be rasterized this frame.

    ``points`` is now 3 x (x, y, z, w) — this step starts carrying the full
    vec4 through projection so the original depth ``w`` survives for the
    perspective-correct texture interpolation.
    """

    points: np.ndarray = field(default_factory=lambda: np.zeros((3, 4)))  # 3 x (x, y, z, w)
    texcoords: list[tex2_t] = field(default_factory=list)  # 3 UV pairs
    color: int = 0xFFFFFFFF
    avg_depth: float = 0.0


###############################################################################
# Shared bounding-box + barycentric-grid setup for both rasterizers
###############################################################################
def _rasterize_setup(
    x0: int, y0: int, x1: int, y1: int, x2: int, y2: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, tuple[int, int, int, int]] | None:
    """Steps 1-3 of the barycentric bounding-box rasterizer (module docstring).

    Returns ``(alpha, beta, gamma, (x_min, x_max, y_min, y_max))`` where the
    weight arrays have shape ``(y_max - y_min + 1, x_max - x_min + 1)``, or
    ``None`` when the triangle is degenerate or entirely off screen.

    The weight formula is exactly the C ``barycentric_weights`` evaluated for
    every pixel in the box at once:

        alpha = ||PC x PB|| / ||AC x AB||    (area opposite vertex A)
        beta  = ||AC x AP|| / ||AC x AB||    (area opposite vertex B)
        gamma = 1 - alpha - beta
    """
    # Step 1: clipped integer bounding box of the triangle.
    x_min = max(min(x0, x1, x2), 0)
    x_max = min(max(x0, x1, x2), display.window_width - 1)
    y_min = max(min(y0, y1, y2), 0)
    y_max = min(max(y0, y1, y2), display.window_height - 1)
    if x_min > x_max or y_min > y_max:
        return None

    # Signed area of the parallelogram spanned by AC and AB. Zero means the
    # three points are collinear — nothing to fill.
    ac_x, ac_y = x2 - x0, y2 - y0
    ab_x, ab_y = x1 - x0, y1 - y0
    area_parallelogram_abc = ac_x * ab_y - ac_y * ab_x
    if area_parallelogram_abc == 0:
        return None

    # Step 2: open pixel grid over the bounding box. Broadcasting a column of
    # y values against a row of x values gives 2-D results without
    # materializing a full meshgrid.
    pxs = np.arange(x_min, x_max + 1, dtype=np.float64)  # (nx,)
    pys = np.arange(y_min, y_max + 1, dtype=np.float64)[:, None]  # (ny, 1)

    # Vectors from/to the sample points (same names as the C code).
    pc_x = x2 - pxs
    pc_y = y2 - pys
    pb_x = x1 - pxs
    pb_y = y1 - pys
    ap_x = pxs - x0
    ap_y = pys - y0

    # Step 3: the three weights for every pixel at once.
    alpha = (pc_x * pb_y - pc_y * pb_x) / area_parallelogram_abc
    beta = (ac_x * ap_y - ac_y * ap_x) / area_parallelogram_abc
    gamma = 1.0 - alpha - beta

    return alpha, beta, gamma, (x_min, x_max, y_min, y_max)


###############################################################################
# Draw a filled triangle with the flat-top/flat-bottom method
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
    """Fill a triangle with a single flat-shaded color.

    Mirrors the C draw_filled_triangle (fill_flat_bottom_triangle +
    fill_flat_top_triangle scanline split), replaced by the vectorized
    barycentric bounding-box rasterizer described in the module docstring.
    The barycentric weights are winding-independent (numerator and
    denominator areas share the same sign), so triangles fill correctly
    whichever way they face.
    """
    # C truncates the float screen coordinates through its `int` parameters.
    x0, y0, x1, y1, x2, y2 = int(x0), int(y0), int(x1), int(y1), int(x2), int(y2)

    setup = _rasterize_setup(x0, y0, x1, y1, x2, y2)
    if setup is None:
        return
    alpha, beta, gamma, (x_min, x_max, y_min, y_max) = setup

    # A pixel is inside the triangle when all three weights are non-negative.
    inside = (alpha >= 0) & (beta >= 0) & (gamma >= 0)

    # One fancy-indexed store into the color buffer.
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
# Return the barycentric weights alpha, beta, and gamma for point p
###############################################################################
#
#         (B)
#         /|\
#        / | \
#       /  |  \
#      /  (P)  \
#     /  /   \  \
#    / /       \ \
#   //           \\
#  (A)------------(C)
#
###############################################################################
def barycentric_weights(a: Vec2, b: Vec2, c: Vec2, p: Vec2) -> Vec3:
    """Scalar barycentric weights of point p inside triangle ABC.

    Kept for readability/parity with the C code; the rasterizers above apply
    the identical formula to whole pixel grids at once.
    """
    # Find the vectors between the vertices ABC and point p
    ac = vec2_sub(c, a)
    ab = vec2_sub(b, a)
    ap = vec2_sub(p, a)
    pc = vec2_sub(c, p)
    pb = vec2_sub(b, p)

    # Compute the area of the full parallelogram/triangle ABC using 2D cross product
    area_parallelogram_abc = ac[0] * ab[1] - ac[1] * ab[0]  # || AC x AB ||

    # Alpha is the area of the small parallelogram/triangle PBC divided by the area of the full parallelogram/triangle ABC
    alpha = (pc[0] * pb[1] - pc[1] * pb[0]) / area_parallelogram_abc

    # Beta is the area of the small parallelogram/triangle APC divided by the area of the full parallelogram/triangle ABC
    beta = (ac[0] * ap[1] - ac[1] * ap[0]) / area_parallelogram_abc

    # Weight gamma is easily found since barycentric coordinates always add up to 1.0
    gamma = 1 - alpha - beta

    return np.array([alpha, beta, gamma], dtype=np.float64)


###############################################################################
# Draw a textured triangle with perspective-correct interpolation
###############################################################################
#
#        v0
#        /\
#       /  \
#      /    \
#     /      \
#   v1--------\
#     \_       \
#        \_     \
#           \_   \
#              \_ \
#                 \\
#                   \
#                    v2
#
###############################################################################
def draw_textured_triangle(
    x0: float, y0: float, z0: float, w0: float, u0: float, v0: float,
    x1: float, y1: float, z1: float, w1: float, u1: float, v1: float,
    x2: float, y2: float, z2: float, w2: float, u2: float, v2: float,
    texture: np.ndarray | None,
) -> None:
    """Texture-map a triangle with perspective-correct interpolation.

    Mirrors the C draw_textured_triangle + draw_texel pair using the
    vectorized barycentric bounding-box rasterizer. The perspective-correct
    part (new in this step): u/w, v/w and 1/w are interpolated linearly
    across the screen, then each pixel recovers u = (u/w)/(1/w) and
    v = (v/w)/(1/w), undoing the perspective distortion step 38 suffered.

    Texel lookup matches the C code's ``abs((int)(u * texture_width))``
    (truncate toward zero, absolute value), plus a modulo wrap so the
    u == 1.0 / v == 1.0 edge cannot index one texel past the texture — the
    C code reads out of bounds there (harmless in C, an IndexError in NumPy).
    """
    if texture is None:
        return

    # Flip the V component to account for inverted UV-coordinates (V grows
    # downwards in the texture, upwards in OBJ files) — new in step 42.
    v0 = 1.0 - v0
    v1 = 1.0 - v1
    v2 = 1.0 - v2

    # C truncates the float screen coordinates through its `int` parameters.
    x0, y0, x1, y1, x2, y2 = int(x0), int(y0), int(x1), int(y1), int(x2), int(y2)

    setup = _rasterize_setup(x0, y0, x1, y1, x2, y2)
    if setup is None:
        return
    alpha, beta, gamma, (x_min, x_max, y_min, y_max) = setup

    # A pixel is inside the triangle when all three weights are non-negative.
    inside = (alpha >= 0) & (beta >= 0) & (gamma >= 0)
    if not inside.any():
        return

    # From here on, work only on the covered pixels (1-D arrays) — faster,
    # and it never divides by 1/w values of pixels we discard anyway.
    alpha_m = alpha[inside]
    beta_m = beta[inside]
    gamma_m = gamma[inside]

    # Perform the interpolation of all U/w and V/w values using barycentric
    # weights and a factor of 1/w (these ARE linear in screen space)...
    interpolated_u = (u0 / w0) * alpha_m + (u1 / w1) * beta_m + (u2 / w2) * gamma_m
    interpolated_v = (v0 / w0) * alpha_m + (v1 / w1) * beta_m + (v2 / w2) * gamma_m

    # Also interpolate the value of 1/w for the current pixel
    interpolated_reciprocal_w = (1 / w0) * alpha_m + (1 / w1) * beta_m + (1 / w2) * gamma_m

    # Now we can divide back both interpolated values by 1/w
    interpolated_u /= interpolated_reciprocal_w
    interpolated_v /= interpolated_reciprocal_w

    # Adjust 1/w so the pixels that are closer to the camera have smaller
    # values (1/w grows toward the camera, so flip it) — new in step 44
    adjusted_reciprocal_w = 1.0 - interpolated_reciprocal_w

    # Map the UV coordinates to texel indices exactly like the C code:
    # tex_x = abs((int)(u * width)) — astype(int64) truncates toward zero
    # like a C cast — then wrap with % so u == 1.0 stays in bounds.
    texture_width = texture_module.texture_width
    texture_height = texture_module.texture_height
    tex_x = np.abs((interpolated_u * texture_width).astype(np.int64)) % texture_width
    tex_y = np.abs((interpolated_v * texture_height).astype(np.int64)) % texture_height

    # Only draw pixels whose depth is less than what the z-buffer holds
    # (C: a per-pixel if inside draw_texel; here: one boolean mask), then
    # store texels and depths with fancy-indexed assignments — new in step 44.
    assert display.color_buffer is not None and display.z_buffer is not None
    z_slice = display.z_buffer[y_min : y_max + 1, x_min : x_max + 1]
    visible = adjusted_reciprocal_w < z_slice[inside]

    color_slice = display.color_buffer[y_min : y_max + 1, x_min : x_max + 1]
    # Compose the final 2-D mask: inside the triangle AND in front.
    draw_mask = inside.copy()
    draw_mask[inside] = visible
    color_slice[draw_mask] = texture[tex_y[visible], tex_x[visible]]
    z_slice[draw_mask] = adjusted_reciprocal_w[visible].astype(np.float32)
