"""clipping.py — mirrors src/clipping.c.

Owns the six view-frustum planes and the polygon clipping routines. The
Sutherland–Hodgman algorithm clips the polygon against one plane at a time,
keeping inside vertices and inserting an intersection point wherever an
edge crosses the plane.

A plane is stored as a point P and a normal N. A vertex Q is *inside* the
plane when ``dot(Q - P, N) > 0``. When consecutive vertices sit on opposite
sides (the two dot products have opposite signs), the crossing point is

    I = previous + t * (current - previous),  t = prev_dot / (prev_dot - cur_dot)

NEW in this step: ``triangles_from_polygon`` fan-triangulates the clipped
polygon back into triangles (n vertices -> n - 2 triangles), so the clipped
result is finally what gets projected and drawn. The C code also renames
``create_polygon_from_triangle`` to ``polygon_from_triangle``.

These loops run over at most MAX_NUM_POLY_VERTICES (10) vertices per
triangle — they are per-vertex, not per-pixel, so plain Python is fine.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from triangle import triangle_t
from texture import tex2_clone, tex2_t
from vector import (
    Vec3,
    vec3_add,
    vec3_clone,
    vec3_dot,
    vec3_mul,
    vec3_new,
    vec3_sub,
    vec4_from_vec3,
)

MAX_NUM_POLY_VERTICES = 10
MAX_NUM_POLY_TRIANGLES = 10

NUM_PLANES = 6

# enum of frustum plane indices
LEFT_FRUSTUM_PLANE = 0
RIGHT_FRUSTUM_PLANE = 1
TOP_FRUSTUM_PLANE = 2
BOTTOM_FRUSTUM_PLANE = 3
NEAR_FRUSTUM_PLANE = 4
FAR_FRUSTUM_PLANE = 5


@dataclass
class plane_t:
    """A frustum plane defined by a point on the plane and its (inward) normal."""

    point: Vec3 = field(default_factory=lambda: vec3_new(0, 0, 0))
    normal: Vec3 = field(default_factory=lambda: vec3_new(0, 0, 0))


@dataclass
class polygon_t:
    """A polygon with up to MAX_NUM_POLY_VERTICES vertices (starts as a triangle)."""

    vertices: list[Vec3] = field(default_factory=list)
    texcoords: list[tex2_t] = field(default_factory=list)  # new in step 54
    num_vertices: int = 0


# Module-level state — mirrors `plane_t frustum_planes[NUM_PLANES]` in clipping.c.
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
def init_frustum_planes(fov_x: float, fov_y: float, z_near: float, z_far: float) -> None:
    """Build the six frustum planes from the horizontal/vertical FOV and near/far distances.

    NEW in this step: the left/right planes use the *horizontal* field of view
    (fov_x) while the top/bottom planes use the *vertical* one (fov_y), so the
    side planes finally match a non-square window's real frustum.
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

    frustum_planes[NEAR_FRUSTUM_PLANE].point = vec3_new(0, 0, z_near)
    frustum_planes[NEAR_FRUSTUM_PLANE].normal = vec3_new(0, 0, 1)

    frustum_planes[FAR_FRUSTUM_PLANE].point = vec3_new(0, 0, z_far)
    frustum_planes[FAR_FRUSTUM_PLANE].normal = vec3_new(0, 0, -1)


def polygon_from_triangle(
    v0: Vec3, v1: Vec3, v2: Vec3, t0: tex2_t, t1: tex2_t, t2: tex2_t
) -> polygon_t:
    """Wrap the triangle's vertices AND texture coordinates for clipping."""
    polygon = polygon_t(vertices=[v0, v1, v2], texcoords=[t0, t1, t2], num_vertices=3)
    return polygon


def triangles_from_polygon(polygon: polygon_t) -> list[triangle_t]:
    """Fan-triangulate the clipped polygon back into individual triangles.

    Every triangle shares vertex 0 of the polygon: (0,1,2), (0,2,3), ...
    A convex polygon with n vertices always yields n - 2 triangles.

    Deviation from C for clarity: the C version fills a caller-provided
    ``triangle_t triangles[]`` array and an out-parameter count; here we
    simply return the list (its length is the count).
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
    """Linear interpolation a + t(b - a) — new in step 54.

    The same factor t that places the intersection point along the clipped
    edge also places the new texture coordinate along the UV edge.
    """
    return a + t * (b - a)


def clip_polygon_against_plane(polygon: polygon_t, plane: int) -> None:
    """Clip the polygon against one frustum plane (Sutherland–Hodgman step).

    Walks the polygon edges (previous vertex -> current vertex): a vertex on
    the inside of the plane is kept; whenever the edge crosses the plane, the
    intersection point I = previous + t*(current - previous) is inserted.
    New in step 54: the texture coordinates travel WITH the vertices — the
    intersection's UV is lerped with the same t. The polygon is updated in
    place (C: out parameter).
    """
    plane_point = frustum_planes[plane].point
    plane_normal = frustum_planes[plane].normal

    # Declare the lists of inside vertices/texcoords for the final polygon
    inside_vertices: list[Vec3] = []
    inside_texcoords: list[tex2_t] = []

    # Start the previous vertex/texcoord with the LAST polygon entries
    previous_vertex = polygon.vertices[polygon.num_vertices - 1] if polygon.num_vertices > 0 else None
    previous_texcoord = polygon.texcoords[polygon.num_vertices - 1] if polygon.num_vertices > 0 else None

    # Calculate the dot product of the previous vertex against the plane
    previous_dot = (
        vec3_dot(vec3_sub(previous_vertex, plane_point), plane_normal)
        if previous_vertex is not None
        else 0.0
    )

    # Loop all the polygon vertices (C: pointer walk from first to last)
    for index in range(polygon.num_vertices):
        current_vertex = polygon.vertices[index]
        current_texcoord = polygon.texcoords[index]
        current_dot = vec3_dot(vec3_sub(current_vertex, plane_point), plane_normal)

        # If we changed from inside to outside or from outside to inside
        if current_dot * previous_dot < 0:
            # Find the interpolation factor t
            t = previous_dot / (previous_dot - current_dot)

            # Calculate the intersection point I = Qp + t(Qc-Qp), one lerp
            # per component (step 54 rewrote the vec3 chain this way)
            intersection_point = vec3_new(
                float_lerp(previous_vertex[0], current_vertex[0], t),
                float_lerp(previous_vertex[1], current_vertex[1], t),
                float_lerp(previous_vertex[2], current_vertex[2], t),
            )
            # Use the lerp formula to get the interpolated U and V texcoords
            interpolated_texcoord = tex2_t(
                u=float_lerp(previous_texcoord.u, current_texcoord.u, t),
                v=float_lerp(previous_texcoord.v, current_texcoord.v, t),
            )

            # Insert the intersection point/texcoord in the "inside" lists
            inside_vertices.append(vec3_clone(intersection_point))
            inside_texcoords.append(tex2_clone(interpolated_texcoord))

        # Current vertex is inside the plane
        if current_dot > 0:
            inside_vertices.append(vec3_clone(current_vertex))
            inside_texcoords.append(tex2_clone(current_texcoord))

        # Move to the next vertex
        previous_dot = current_dot
        previous_vertex = current_vertex
        previous_texcoord = current_texcoord

    # At the end, copy the inside lists into the destination polygon (out parameter)
    polygon.vertices[: len(inside_vertices)] = [vec3_clone(v) for v in inside_vertices]
    polygon.texcoords[: len(inside_texcoords)] = [tex2_clone(t) for t in inside_texcoords]
    polygon.num_vertices = len(inside_vertices)


def clip_polygon(polygon: polygon_t) -> None:
    """Clip the polygon against all six frustum planes, one after another."""
    clip_polygon_against_plane(polygon, LEFT_FRUSTUM_PLANE)
    clip_polygon_against_plane(polygon, RIGHT_FRUSTUM_PLANE)
    clip_polygon_against_plane(polygon, TOP_FRUSTUM_PLANE)
    clip_polygon_against_plane(polygon, BOTTOM_FRUSTUM_PLANE)
    clip_polygon_against_plane(polygon, NEAR_FRUSTUM_PLANE)
    clip_polygon_against_plane(polygon, FAR_FRUSTUM_PLANE)
