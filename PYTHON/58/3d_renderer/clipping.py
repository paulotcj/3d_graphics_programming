"""clipping.py — mirrors src/clipping.c.

Owns the six view-frustum planes and the polygon clipping machinery. Before a
triangle is projected to the screen it is clipped, in camera space, against
the six planes of the viewing frustum (left, right, top, bottom, near, far).
Clipping can turn a triangle into a polygon with up to 10 vertices
(``MAX_NUM_POLY_VERTICES``); that polygon is then fanned back into triangles.

Why clip at all? A vertex behind the camera has w <= 0 and would explode (or
flip) during the perspective divide. Clipping against the near plane removes
those vertices *before* projection, replacing them with interpolated points
that sit exactly on the plane — including interpolated UV coordinates so the
texture keeps flowing smoothly across the cut.

Each plane is stored as a point P and a normal N pointing *inside* the
frustum, so for any vertex Q the signed distance is ``dot(Q - P, N)``:
positive means inside, negative means outside.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from texture import tex2_t, tex2_clone
from triangle import triangle_t
from vector import Vec3, vec3_clone, vec3_dot, vec3_new, vec3_sub, vec4_from_vec3

MAX_NUM_POLY_VERTICES: int = 10
MAX_NUM_POLY_TRIANGLES: int = 10

# enum of frustum plane indices (mirrors the anonymous enum in clipping.h)
LEFT_FRUSTUM_PLANE: int = 0
RIGHT_FRUSTUM_PLANE: int = 1
TOP_FRUSTUM_PLANE: int = 2
BOTTOM_FRUSTUM_PLANE: int = 3
NEAR_FRUSTUM_PLANE: int = 4
FAR_FRUSTUM_PLANE: int = 5

NUM_PLANES: int = 6


@dataclass
class plane_t:
    """A frustum plane: a point on the plane and an inward-facing normal."""

    point: Vec3 = field(default_factory=lambda: vec3_new(0, 0, 0))
    normal: Vec3 = field(default_factory=lambda: vec3_new(0, 0, 0))


@dataclass
class polygon_t:
    """A convex polygon produced by clipping a triangle.

    In C this is two fixed arrays of MAX_NUM_POLY_VERTICES entries plus a
    count; in Python the lists grow as needed and ``num_vertices`` is kept for
    1:1 parity with the C control flow.
    """

    vertices: list[Vec3] = field(default_factory=list)
    texcoords: list[tex2_t] = field(default_factory=list)
    num_vertices: int = 0


# Module-level state — mirrors the `plane_t frustum_planes[NUM_PLANES]` global.
frustum_planes: list[plane_t] = [plane_t() for _ in range(NUM_PLANES)]


###############################################################################
# Frustum planes are defined by a point and a normal vector
###############################################################################
# Near plane   :  P=(0, 0, znear), N=(0, 0,  1)
# Far plane    :  P=(0, 0, zfar),  N=(0, 0, -1)
# Top plane    :  P=(0, 0, 0),     N=(0, -cos(fovy/2), sin(fovy/2))
# Bottom plane :  P=(0, 0, 0),     N=(0, cos(fovy/2), sin(fovy/2))
# Left plane   :  P=(0, 0, 0),     N=(cos(fovx/2), 0, sin(fovx/2))
# Right plane  :  P=(0, 0, 0),     N=(-cos(fovx/2), 0, sin(fovx/2))
###############################################################################
#
#           /|\
#         /  | |
#       /\   | |
#     /      | |
#  P*|-->  <-|*|   ----> +z-axis
#     \      | |
#       \/   | |
#         \  | |
#           \|/
#
###############################################################################
def init_frustum_planes(fov_x: float, fov_y: float, znear: float, zfar: float) -> None:
    """Build the six frustum planes from the horizontal/vertical FOV and z range.

    The four side planes all pass through the camera origin; their normals
    are tilted inward by half the field-of-view angle (that is where the
    cos/sin of fov/2 come from). The near and far planes are perpendicular
    to the z-axis at znear and zfar.
    """
    cos_half_fov_x = math.cos(fov_x / 2)
    sin_half_fov_x = math.sin(fov_x / 2)
    cos_half_fov_y = math.cos(fov_y / 2)
    sin_half_fov_y = math.sin(fov_y / 2)

    frustum_planes[LEFT_FRUSTUM_PLANE].point = vec3_new(0, 0, 0)
    frustum_planes[LEFT_FRUSTUM_PLANE].normal = vec3_new(cos_half_fov_x, 0, sin_half_fov_x)

    frustum_planes[RIGHT_FRUSTUM_PLANE].point = vec3_new(0, 0, 0)
    frustum_planes[RIGHT_FRUSTUM_PLANE].normal = vec3_new(-cos_half_fov_x, 0, sin_half_fov_x)

    frustum_planes[TOP_FRUSTUM_PLANE].point = vec3_new(0, 0, 0)
    frustum_planes[TOP_FRUSTUM_PLANE].normal = vec3_new(0, -cos_half_fov_y, sin_half_fov_y)

    frustum_planes[BOTTOM_FRUSTUM_PLANE].point = vec3_new(0, 0, 0)
    frustum_planes[BOTTOM_FRUSTUM_PLANE].normal = vec3_new(0, cos_half_fov_y, sin_half_fov_y)

    frustum_planes[NEAR_FRUSTUM_PLANE].point = vec3_new(0, 0, znear)
    frustum_planes[NEAR_FRUSTUM_PLANE].normal = vec3_new(0, 0, 1)

    frustum_planes[FAR_FRUSTUM_PLANE].point = vec3_new(0, 0, zfar)
    frustum_planes[FAR_FRUSTUM_PLANE].normal = vec3_new(0, 0, -1)


def polygon_from_triangle(
    v0: Vec3, v1: Vec3, v2: Vec3, t0: tex2_t, t1: tex2_t, t2: tex2_t
) -> polygon_t:
    """Wrap one camera-space triangle (plus its UVs) into a clippable polygon."""
    return polygon_t(
        vertices=[v0, v1, v2],
        texcoords=[t0, t1, t2],
        num_vertices=3,
    )


def triangles_from_polygon(polygon: polygon_t) -> list[triangle_t]:
    """Fan-triangulate the clipped polygon back into triangles.

    Every triangle shares vertex 0 of the polygon: (0,1,2), (0,2,3), ...
    A convex polygon with n vertices always yields n - 2 triangles.

    Deviation from C for clarity: the C version fills a caller-provided
    array and an out-parameter count; here we simply return the list.
    """
    triangles: list[triangle_t] = []
    for i in range(polygon.num_vertices - 2):
        index0 = 0
        index1 = i + 1
        index2 = i + 2

        triangle = triangle_t()
        triangle.points = np.array(
            [
                vec4_from_vec3(polygon.vertices[index0]),
                vec4_from_vec3(polygon.vertices[index1]),
                vec4_from_vec3(polygon.vertices[index2]),
            ],
            dtype=np.float64,
        )
        triangle.texcoords = [
            polygon.texcoords[index0],
            polygon.texcoords[index1],
            polygon.texcoords[index2],
        ]
        triangles.append(triangle)
    return triangles


def float_lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation: a when t=0, b when t=1."""
    return a + t * (b - a)


def clip_polygon_against_plane(polygon: polygon_t, plane: int) -> None:
    """Clip the polygon against one frustum plane, in place (Sutherland-Hodgman).

    Walk the polygon edges (previous vertex -> current vertex). For each edge:

    - If the edge *crosses* the plane (the two signed distances have opposite
      signs), compute the intersection point with ``t = d_prev / (d_prev -
      d_curr)`` and lerp both the position and the UV coordinate — this is
      what keeps textures continuous across the clipped edge.
    - If the current vertex is inside (positive distance), keep it.

    The surviving vertices replace the polygon's contents.
    """
    # An earlier plane may have clipped the polygon away entirely; the C code
    # relies on its while-loop simply not executing, Python needs the guard
    # before indexing vertices[-1].
    if polygon.num_vertices == 0:
        return

    plane_point = frustum_planes[plane].point
    plane_normal = frustum_planes[plane].normal

    # Declare the array of inside vertices that will become the final polygon
    inside_vertices: list[Vec3] = []
    inside_texcoords: list[tex2_t] = []

    # Start the previous vertex with the last polygon vertex and texture coordinate
    previous_vertex = polygon.vertices[polygon.num_vertices - 1]
    previous_texcoord = polygon.texcoords[polygon.num_vertices - 1]

    # Signed distance of the previous vertex from the plane
    previous_dot = vec3_dot(vec3_sub(previous_vertex, plane_point), plane_normal)

    # Loop all the polygon vertices (C: pointer walk from first to last)
    for i in range(polygon.num_vertices):
        current_vertex = polygon.vertices[i]
        current_texcoord = polygon.texcoords[i]
        current_dot = vec3_dot(vec3_sub(current_vertex, plane_point), plane_normal)

        # If we changed from inside to outside or from outside to inside
        if current_dot * previous_dot < 0:
            # Find the interpolation factor t
            t = previous_dot / (previous_dot - current_dot)

            # Calculate the intersection point I = Q1 + t(Q2-Q1)
            intersection_point = vec3_new(
                float_lerp(previous_vertex[0], current_vertex[0], t),
                float_lerp(previous_vertex[1], current_vertex[1], t),
                float_lerp(previous_vertex[2], current_vertex[2], t),
            )

            # Use the lerp formula to get the interpolated U and V texture coordinates
            interpolated_texcoord = tex2_t(
                u=float_lerp(previous_texcoord.u, current_texcoord.u, t),
                v=float_lerp(previous_texcoord.v, current_texcoord.v, t),
            )

            # Insert the intersection point to the list of "inside vertices"
            inside_vertices.append(vec3_clone(intersection_point))
            inside_texcoords.append(tex2_clone(interpolated_texcoord))

        # Current vertex is inside the plane
        if current_dot > 0:
            # Insert the current vertex to the list of "inside vertices"
            inside_vertices.append(vec3_clone(current_vertex))
            inside_texcoords.append(tex2_clone(current_texcoord))

        # Move to the next vertex
        previous_dot = current_dot
        previous_vertex = current_vertex
        previous_texcoord = current_texcoord

    # At the end, copy the list of inside vertices into the polygon (in place)
    polygon.vertices = inside_vertices
    polygon.texcoords = inside_texcoords
    polygon.num_vertices = len(inside_vertices)


def clip_polygon(polygon: polygon_t) -> None:
    """Clip the polygon against all six frustum planes, one after another."""
    clip_polygon_against_plane(polygon, LEFT_FRUSTUM_PLANE)
    clip_polygon_against_plane(polygon, RIGHT_FRUSTUM_PLANE)
    clip_polygon_against_plane(polygon, TOP_FRUSTUM_PLANE)
    clip_polygon_against_plane(polygon, BOTTOM_FRUSTUM_PLANE)
    clip_polygon_against_plane(polygon, NEAR_FRUSTUM_PLANE)
    clip_polygon_against_plane(polygon, FAR_FRUSTUM_PLANE)
