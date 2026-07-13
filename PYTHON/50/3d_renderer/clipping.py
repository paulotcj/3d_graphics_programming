"""clipping.py — mirrors src/clipping.c / src/clipping.h of C step 50.

Defines the six **frustum planes** that will clip geometry in the next
steps. Each plane is a point plus an inward-pointing normal:

    Near   : P=(0, 0, znear), N=(0, 0, 1)
    Far    : P=(0, 0, zfar),  N=(0, 0, -1)
    Top    : P=(0, 0, 0),     N=(0, -cos(fov/2), sin(fov/2))
    Bottom : P=(0, 0, 0),     N=(0,  cos(fov/2), sin(fov/2))
    Left   : P=(0, 0, 0),     N=( cos(fov/2), 0, sin(fov/2))
    Right  : P=(0, 0, 0),     N=(-cos(fov/2), 0, sin(fov/2))

The four side planes pass through the camera origin, tilted half the field
of view outward; sin/cos of fov/2 build their normals.

New in step 50: the ``polygon_t`` type and the clip_polygon() pipeline — a
triangle becomes a polygon (up to MAX_NUM_POLY_VERTICES corners) that gets
clipped against all six planes in turn. The per-plane routine is still a
TODO (exactly as in the C); the real Sutherland-Hodgman algorithm lands in
step 51.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from vector import Vec3

# Plane indices — mirrors the C enum
LEFT_FRUSTUM_PLANE = 0
RIGHT_FRUSTUM_PLANE = 1
TOP_FRUSTUM_PLANE = 2
BOTTOM_FRUSTUM_PLANE = 3
NEAR_FRUSTUM_PLANE = 4
FAR_FRUSTUM_PLANE = 5

NUM_PLANES = 6


@dataclass
class plane_t:
    """A frustum plane: a point on the plane and its inward normal."""

    point: Vec3 = field(default_factory=lambda: np.zeros(3))
    normal: Vec3 = field(default_factory=lambda: np.zeros(3))


# C: plane_t frustum_planes[NUM_PLANES]
frustum_planes: list[plane_t] = [plane_t() for _ in range(NUM_PLANES)]


def init_frustum_planes(fov: float, z_near: float, z_far: float) -> None:
    """Build the six planes from the field of view and the near/far depths."""
    cos_half_fov = math.cos(fov / 2)
    sin_half_fov = math.sin(fov / 2)

    frustum_planes[LEFT_FRUSTUM_PLANE].point = np.array([0.0, 0.0, 0.0])
    frustum_planes[LEFT_FRUSTUM_PLANE].normal = np.array([cos_half_fov, 0.0, sin_half_fov])

    frustum_planes[RIGHT_FRUSTUM_PLANE].point = np.array([0.0, 0.0, 0.0])
    frustum_planes[RIGHT_FRUSTUM_PLANE].normal = np.array([-cos_half_fov, 0.0, sin_half_fov])

    frustum_planes[TOP_FRUSTUM_PLANE].point = np.array([0.0, 0.0, 0.0])
    frustum_planes[TOP_FRUSTUM_PLANE].normal = np.array([0.0, -cos_half_fov, sin_half_fov])

    frustum_planes[BOTTOM_FRUSTUM_PLANE].point = np.array([0.0, 0.0, 0.0])
    frustum_planes[BOTTOM_FRUSTUM_PLANE].normal = np.array([0.0, cos_half_fov, sin_half_fov])

    frustum_planes[NEAR_FRUSTUM_PLANE].point = np.array([0.0, 0.0, z_near])
    frustum_planes[NEAR_FRUSTUM_PLANE].normal = np.array([0.0, 0.0, 1.0])

    frustum_planes[FAR_FRUSTUM_PLANE].point = np.array([0.0, 0.0, z_far])
    frustum_planes[FAR_FRUSTUM_PLANE].normal = np.array([0.0, 0.0, -1.0])


###############################################################################
# Polygon clipping (skeleton — new in step 50)
###############################################################################
MAX_NUM_POLY_VERTICES = 10  # a triangle clipped by 6 planes can gain corners


@dataclass
class polygon_t:
    """A clip-in-progress polygon: its vertices and how many are valid."""

    vertices: list[Vec3] = field(default_factory=list)
    num_vertices: int = 0


def create_polygon_from_triangle(v0: Vec3, v1: Vec3, v2: Vec3) -> polygon_t:
    """Wrap a triangle's three vertices into a polygon ready for clipping."""
    return polygon_t(vertices=[v0, v1, v2], num_vertices=3)


def clip_polygon_against_plane(polygon: polygon_t, plane: int) -> None:
    """Clip the polygon against ONE frustum plane — still a TODO, as in the C.

    Step 51 implements the Sutherland-Hodgman walk here.
    """
    # TODO:...


def clip_polygon(polygon: polygon_t) -> None:
    """Clip the polygon against all six frustum planes, one at a time."""
    clip_polygon_against_plane(polygon, LEFT_FRUSTUM_PLANE)
    clip_polygon_against_plane(polygon, RIGHT_FRUSTUM_PLANE)
    clip_polygon_against_plane(polygon, TOP_FRUSTUM_PLANE)
    clip_polygon_against_plane(polygon, BOTTOM_FRUSTUM_PLANE)
    clip_polygon_against_plane(polygon, NEAR_FRUSTUM_PLANE)
    clip_polygon_against_plane(polygon, FAR_FRUSTUM_PLANE)
