"""clipping.py — mirrors src/clipping.c.

Owns the six view-frustum planes and the polygon clipping routines. This is
the step where ``clip_polygon_against_plane`` gains its real implementation:
the Sutherland–Hodgman algorithm clips the polygon against one plane at a
time, keeping inside vertices and inserting an intersection point wherever
an edge crosses the plane.

A plane is stored as a point P and a normal N. A vertex Q is *inside* the
plane when ``dot(Q - P, N) > 0``. When consecutive vertices sit on opposite
sides (the two dot products have opposite signs), the crossing point is

    I = previous + t * (current - previous),  t = prev_dot / (prev_dot - cur_dot)

Note: at this step main.c only *builds and clips* the polygon — the clipped
result is not yet broken back into triangles (that is the next lesson), so
clipping does not change what is drawn yet.

These loops run over at most MAX_NUM_POLY_VERTICES (10) vertices per
triangle — they are per-vertex, not per-pixel, so plain Python is fine.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from vector import (
    Vec3,
    vec3_add,
    vec3_clone,
    vec3_dot,
    vec3_mul,
    vec3_new,
    vec3_sub,
)

MAX_NUM_POLY_VERTICES = 10

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
    num_vertices: int = 0


# Module-level state — mirrors `plane_t frustum_planes[NUM_PLANES]` in clipping.c.
frustum_planes: list[plane_t] = [plane_t() for _ in range(NUM_PLANES)]


###############################################################################
# Frustum planes are defined by a point and a normal vector
###############################################################################
# Near plane   :  P=(0, 0, znear), N=(0, 0,  1)
# Far plane    :  P=(0, 0, zfar),  N=(0, 0, -1)
# Top plane    :  P=(0, 0, 0),     N=(0, -cos(fov/2), sin(fov/2))
# Bottom plane :  P=(0, 0, 0),     N=(0, cos(fov/2), sin(fov/2))
# Left plane   :  P=(0, 0, 0),     N=(cos(fov/2), 0, sin(fov/2))
# Right plane  :  P=(0, 0, 0),     N=(-cos(fov/2), 0, sin(fov/2))
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
def init_frustum_planes(fov: float, z_near: float, z_far: float) -> None:
    """Build the six frustum planes from the field of view and near/far distances."""
    cos_half_fov = math.cos(fov / 2)
    sin_half_fov = math.sin(fov / 2)

    frustum_planes[LEFT_FRUSTUM_PLANE].point = vec3_new(0, 0, 0)
    frustum_planes[LEFT_FRUSTUM_PLANE].normal = vec3_new(cos_half_fov, 0, sin_half_fov)

    frustum_planes[RIGHT_FRUSTUM_PLANE].point = vec3_new(0, 0, 0)
    frustum_planes[RIGHT_FRUSTUM_PLANE].normal = vec3_new(-cos_half_fov, 0, sin_half_fov)

    frustum_planes[TOP_FRUSTUM_PLANE].point = vec3_new(0, 0, 0)
    frustum_planes[TOP_FRUSTUM_PLANE].normal = vec3_new(0, -cos_half_fov, sin_half_fov)

    frustum_planes[BOTTOM_FRUSTUM_PLANE].point = vec3_new(0, 0, 0)
    frustum_planes[BOTTOM_FRUSTUM_PLANE].normal = vec3_new(0, cos_half_fov, sin_half_fov)

    frustum_planes[NEAR_FRUSTUM_PLANE].point = vec3_new(0, 0, z_near)
    frustum_planes[NEAR_FRUSTUM_PLANE].normal = vec3_new(0, 0, 1)

    frustum_planes[FAR_FRUSTUM_PLANE].point = vec3_new(0, 0, z_far)
    frustum_planes[FAR_FRUSTUM_PLANE].normal = vec3_new(0, 0, -1)


def create_polygon_from_triangle(v0: Vec3, v1: Vec3, v2: Vec3) -> polygon_t:
    """Wrap the three triangle vertices in a polygon ready to be clipped."""
    polygon = polygon_t(vertices=[v0, v1, v2], num_vertices=3)
    return polygon


def clip_polygon_against_plane(polygon: polygon_t, plane: int) -> None:
    """Clip the polygon against one frustum plane (Sutherland–Hodgman step).

    Walks the polygon edges (previous vertex -> current vertex): a vertex on
    the inside of the plane is kept; whenever the edge crosses the plane, the
    intersection point I = previous + t*(current - previous) is inserted.
    The polygon is updated in place (C: out parameter).
    """
    plane_point = frustum_planes[plane].point
    plane_normal = frustum_planes[plane].normal

    # Declare the list of inside vertices that will be part of the final polygon
    inside_vertices: list[Vec3] = []

    # Start the current vertex with the first polygon vertex, and the previous with the last polygon vertex
    previous_vertex = polygon.vertices[polygon.num_vertices - 1] if polygon.num_vertices > 0 else None

    # Calculate the dot product of the previous vertex against the plane
    previous_dot = (
        vec3_dot(vec3_sub(previous_vertex, plane_point), plane_normal)
        if previous_vertex is not None
        else 0.0
    )

    # Loop all the polygon vertices (C: pointer walk from first to last)
    for index in range(polygon.num_vertices):
        current_vertex = polygon.vertices[index]
        current_dot = vec3_dot(vec3_sub(current_vertex, plane_point), plane_normal)

        # If we changed from inside to outside or from outside to inside
        if current_dot * previous_dot < 0:
            # Find the interpolation factor t
            t = previous_dot / (previous_dot - current_dot)
            # Calculate the intersection point I = Q1 + t(Q2-Q1)
            intersection_point = vec3_clone(current_vertex)
            intersection_point = vec3_sub(intersection_point, previous_vertex)
            intersection_point = vec3_mul(intersection_point, t)
            intersection_point = vec3_add(intersection_point, previous_vertex)
            # Insert the intersection point to the list of "inside vertices"
            inside_vertices.append(vec3_clone(intersection_point))

        # Current vertex is inside the plane
        if current_dot > 0:
            # Insert the current vertex to the list of "inside vertices"
            inside_vertices.append(vec3_clone(current_vertex))

        # Move to the next vertex
        previous_dot = current_dot
        previous_vertex = current_vertex

    # At the end, copy the list of inside vertices into the destination polygon (out parameter)
    polygon.vertices[: len(inside_vertices)] = [vec3_clone(v) for v in inside_vertices]
    polygon.num_vertices = len(inside_vertices)


def clip_polygon(polygon: polygon_t) -> None:
    """Clip the polygon against all six frustum planes, one after another."""
    clip_polygon_against_plane(polygon, LEFT_FRUSTUM_PLANE)
    clip_polygon_against_plane(polygon, RIGHT_FRUSTUM_PLANE)
    clip_polygon_against_plane(polygon, TOP_FRUSTUM_PLANE)
    clip_polygon_against_plane(polygon, BOTTOM_FRUSTUM_PLANE)
    clip_polygon_against_plane(polygon, NEAR_FRUSTUM_PLANE)
    clip_polygon_against_plane(polygon, FAR_FRUSTUM_PLANE)
