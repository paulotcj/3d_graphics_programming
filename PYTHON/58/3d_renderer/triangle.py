"""triangle.py — mirrors src/triangle.c.

Owns the ``face_t`` / ``triangle_t`` types, the barycentric-weights math,
the face-normal helper ``get_triangle_normal`` (NEW in step 58 — moved here
from main.c's update loop), and the three triangle drawing routines
(wireframe, flat-shaded filled, perspective-correct textured).

Rasterization strategy (CONVENTIONS.md §5): the C code fills triangles with
a flat-top/flat-bottom *scanline* loop that calls draw_triangle_pixel /
draw_triangle_texel once per pixel. A per-pixel Python loop would be ~100x
too slow, so both filled and textured triangles use the **barycentric
bounding-box rasterizer** instead:

1. Compute the triangle's screen-space bounding box, clipped to the window.
2. Evaluate the barycentric weights (alpha, beta, gamma) for *every* pixel
   in the box at once with NumPy broadcasting — the exact same formula the
   C ``barycentric_weights`` uses, just on arrays.
3. ``inside = (alpha >= 0) & (beta >= 0) & (gamma >= 0)`` selects the pixels
   covered by the triangle.
4. Interpolate ``1/w`` (and ``u/w``, ``v/w`` for textures) as array math.
5. Depth-test with a boolean mask against the z-buffer slice and store the
   surviving pixels with one fancy-indexed assignment.

The result is visually identical to the C scanline fill, hundreds of times
faster than looping in Python.

Why interpolate 1/w and u/w instead of w and u? Perspective projection is
not linear in screen space — a texture point halfway across a triangle on
screen is NOT halfway across it in 3D. But 1/w and u/w *are* linear in
screen space, so we interpolate those and recover u = (u/w) / (1/w) per
pixel. That is what "perspective-correct texture mapping" means.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

import display
from texture import tex2_t, texture_t
from vector import (
    Vec2,
    Vec3,
    vec2_sub,
    vec3_cross,
    vec3_from_vec4,
    vec3_normalize,
    vec3_sub,
)


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
    """A screen-space triangle ready to be rasterized this frame."""

    points: np.ndarray = field(default_factory=lambda: np.zeros((3, 4)))  # 3 x (x, y, z, w)
    texcoords: list[tex2_t] = field(default_factory=list)  # 3 UV pairs
    color: int = 0xFFFFFFFF
    texture: texture_t | None = None


###############################################################################
# Return the normal vector of a triangle face
###############################################################################
def get_triangle_normal(vertices: np.ndarray) -> Vec3:
    """Compute the (normalized) face normal of a camera-space triangle.

    NEW in step 58: moved here from main.c's update loop. The normal is the
    cross product of the two edges AB and AC; its direction (toward or away
    from the camera) is what backface culling tests.
    """
    # Get individual vectors from A, B, and C vertices to compute normal
    vector_a = vec3_from_vec4(vertices[0])  # /*   A   */
    vector_b = vec3_from_vec4(vertices[1])  # /*  / \  */
    vector_c = vec3_from_vec4(vertices[2])  # /* C---B */

    # Get the vector subtraction of B-A and C-A
    vector_ab = vec3_sub(vector_b, vector_a)
    vector_ac = vec3_sub(vector_c, vector_a)
    vec3_normalize(vector_ab)
    vec3_normalize(vector_ac)

    # Compute the face normal (using cross product to find perpendicular)
    normal = vec3_cross(vector_ab, vector_ac)
    vec3_normalize(normal)

    return normal


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

    Kept for readability/parity with the C code; the rasterizers below apply
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
# Draw a triangle using three raw line calls
###############################################################################
def draw_triangle(x0: int, y0: int, x1: int, y1: int, x2: int, y2: int, color: int) -> None:
    """Draw the wireframe outline of a triangle."""
    x0, y0, x1, y1, x2, y2 = int(x0), int(y0), int(x1), int(y1), int(x2), int(y2)
    display.draw_line(x0, y0, x1, y1, color)
    display.draw_line(x1, y1, x2, y2, color)
    display.draw_line(x2, y2, x0, y0, color)


def _rasterize_setup(
    x0: int, y0: int, x1: int, y1: int, x2: int, y2: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, tuple[int, int, int, int]] | None:
    """Shared bounding-box + barycentric grid setup for both rasterizers.

    Returns ``(alpha, beta, gamma, (x_min, x_max, y_min, y_max))`` where the
    weight arrays have shape ``(y_max - y_min + 1, x_max - x_min + 1)``, or
    ``None`` when the triangle is degenerate or entirely off screen.

    This is steps 1-3 of the barycentric bounding-box rasterizer described in
    the module docstring. The weight formula is exactly the C
    ``barycentric_weights`` evaluated for every pixel in the box at once:

        alpha = ||PC x PB|| / ||AC x AB||    (area opposite vertex A)
        beta  = ||AC x AP|| / ||AC x AB||    (area opposite vertex B)
        gamma = 1 - alpha - beta
    """
    # Clipped integer bounding box of the triangle (step 1).
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

    # Open pixel grid over the bounding box (step 2). Broadcasting a column
    # of y values against a row of x values gives 2-D results without
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

    # The three weights for every pixel at once (step 3).
    alpha = (pc_x * pb_y - pc_y * pb_x) / area_parallelogram_abc
    beta = (ac_x * ap_y - ac_y * ap_x) / area_parallelogram_abc
    gamma = 1.0 - alpha - beta

    return alpha, beta, gamma, (x_min, x_max, y_min, y_max)


###############################################################################
# Draw a filled triangle with depth interpolation (z-buffer)
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
    x0: float, y0: float, z0: float, w0: float,
    x1: float, y1: float, z1: float, w1: float,
    x2: float, y2: float, z2: float, w2: float,
    color: int,
) -> None:
    """Fill a triangle with a single flat-shaded color, z-buffered.

    Mirrors the C draw_filled_triangle + draw_triangle_pixel pair, but
    replaces the scanline-plus-per-pixel-call structure with the vectorized
    barycentric bounding-box rasterizer (see module docstring).
    """
    # C truncates the float screen coordinates through its `int` parameters.
    x0, y0, x1, y1, x2, y2 = int(x0), int(y0), int(x1), int(y1), int(x2), int(y2)

    setup = _rasterize_setup(x0, y0, x1, y1, x2, y2)
    if setup is None:
        return
    alpha, beta, gamma, (x_min, x_max, y_min, y_max) = setup

    # A pixel is inside the triangle when all three weights are non-negative.
    inside = (alpha >= 0) & (beta >= 0) & (gamma >= 0)

    # Interpolate the value of 1/w for every candidate pixel (1/w IS linear
    # in screen space, so a plain weighted sum is correct — see docstring).
    interpolated_reciprocal_w = (1.0 / w0) * alpha + (1.0 / w1) * beta + (1.0 / w2) * gamma

    # Adjust 1/w so the pixels that are closer to the camera have smaller values
    interpolated_reciprocal_w = 1.0 - interpolated_reciprocal_w

    # Only draw pixels whose depth value is less than the one already in the
    # z-buffer (vectorized version of the C per-pixel comparison).
    assert display.color_buffer is not None and display.z_buffer is not None
    z_slice = display.z_buffer[y_min : y_max + 1, x_min : x_max + 1]
    mask = inside & (interpolated_reciprocal_w < z_slice)

    color_slice = display.color_buffer[y_min : y_max + 1, x_min : x_max + 1]
    color_slice[mask] = color
    z_slice[mask] = interpolated_reciprocal_w[mask].astype(np.float32)


###############################################################################
# Draw a textured triangle with perspective-correct interpolation (z-buffer)
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
    texture: texture_t | None,
) -> None:
    """Texture-map a triangle with perspective correction, z-buffered.

    Mirrors the C draw_textured_triangle + draw_triangle_texel pair using the
    vectorized barycentric bounding-box rasterizer. The perspective-correct
    part: u/w, v/w and 1/w are interpolated linearly across the screen, then
    each pixel recovers u = (u/w)/(1/w), v = (v/w)/(1/w).
    """
    if texture is None:
        return

    # C truncates the float screen coordinates through its `int` parameters.
    x0, y0, x1, y1, x2, y2 = int(x0), int(y0), int(x1), int(y1), int(x2), int(y2)

    # Flip the V component to account for inverted UV-coordinates (V grows downwards)
    v0 = 1.0 - v0
    v1 = 1.0 - v1
    v2 = 1.0 - v2

    setup = _rasterize_setup(x0, y0, x1, y1, x2, y2)
    if setup is None:
        return
    alpha, beta, gamma, (x_min, x_max, y_min, y_max) = setup

    # A pixel is inside the triangle when all three weights are non-negative.
    inside = (alpha >= 0) & (beta >= 0) & (gamma >= 0)

    # Interpolate 1/w for every candidate pixel, then apply the same
    # "closer pixels get smaller values" adjustment as the C code.
    interpolated_reciprocal_w = (1.0 / w0) * alpha + (1.0 / w1) * beta + (1.0 / w2) * gamma
    adjusted_reciprocal_w = 1.0 - interpolated_reciprocal_w

    # Vectorized z-test: keep pixels inside the triangle that are closer than
    # what the z-buffer already holds.
    assert display.color_buffer is not None and display.z_buffer is not None
    z_slice = display.z_buffer[y_min : y_max + 1, x_min : x_max + 1]
    mask = inside & (adjusted_reciprocal_w < z_slice)
    if not mask.any():
        return

    # From here on, work only on the surviving pixels (1-D arrays) — this is
    # both faster and avoids dividing by 1/w values of pixels we discard.
    alpha_m = alpha[mask]
    beta_m = beta[mask]
    gamma_m = gamma[mask]
    reciprocal_w_m = interpolated_reciprocal_w[mask]

    # Perform the interpolation of all U/w and V/w values using barycentric
    # weights and a factor of 1/w (linear in screen space)...
    interpolated_u = (u0 / w0) * alpha_m + (u1 / w1) * beta_m + (u2 / w2) * gamma_m
    interpolated_v = (v0 / w0) * alpha_m + (v1 / w1) * beta_m + (v2 / w2) * gamma_m

    # ...then divide back by 1/w to undo the perspective distortion.
    interpolated_u /= reciprocal_w_m
    interpolated_v /= reciprocal_w_m

    # Map the UV coordinates to texel indices exactly like the C code:
    # tex_x = abs((int)(u * width)) % width — truncate toward zero, absolute
    # value, then wrap. (astype(int64) truncates toward zero like a C cast.)
    texture_width = texture.width
    texture_height = texture.height
    tex_x = np.abs((interpolated_u * texture_width).astype(np.int64)) % texture_width
    tex_y = np.abs((interpolated_v * texture_height).astype(np.int64)) % texture_height

    # Texture sample per pixel via fancy indexing, stored with one assignment.
    color_slice = display.color_buffer[y_min : y_max + 1, x_min : x_max + 1]
    color_slice[mask] = texture.texels[tex_y, tex_x]
    z_slice[mask] = adjusted_reciprocal_w[mask].astype(np.float32)
