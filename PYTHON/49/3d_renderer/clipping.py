"""clipping.py — mirrors src/clipping.c / src/clipping.h of C step 49.

Defines the six **frustum planes** that will clip geometry in the next
steps. Each plane is a point plus an inward-pointing normal:

    Near   : P=(0, 0, znear), N=(0, 0, 1)
    Far    : P=(0, 0, zfar),  N=(0, 0, -1)
    Top    : P=(0, 0, 0),     N=(0, -cos(fov/2), sin(fov/2))
    Bottom : P=(0, 0, 0),     N=(0,  cos(fov/2), sin(fov/2))
    Left   : P=(0, 0, 0),     N=( cos(fov/2), 0, sin(fov/2))
    Right  : P=(0, 0, 0),     N=(-cos(fov/2), 0, sin(fov/2))

The four side planes pass through the camera origin, tilted half the field
of view outward; sin/cos of fov/2 build their normals. Nothing uses the
planes yet — this step only *defines* them (clipping arrives in 50-52).
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
