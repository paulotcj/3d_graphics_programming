"""vector.py — mirrors src/vector.c and src/vector.h.

Owns the 2D/3D vector helpers. A "vector" in this conversion is a small NumPy
``float64`` array (length 2 or 3), so the C struct fields map to indices:
``v.x`` -> ``v[0]``, ``v.y`` -> ``v[1]``, ``v.z`` -> ``v[2]``.

At this step the C file implements exactly three functions — the per-axis
rotations that step 15 introduces to spin the point cloud. The rotation math
comes from the angle-addition identities (quoted from the C comments):

    cos(a + b) = cos(a)*cos(b) - sin(a)*sin(b)
    sin(a + b) = sin(a)*cos(b) + cos(a)*sin(b)

Rotating a point (x, y) of angle a by an extra angle b and expanding those
identities gives the classic 2D rotation applied to the two axes that move,
while the axis being rotated *around* stays untouched.
"""

from __future__ import annotations

import math

import numpy as np

# Type aliases: both are plain NumPy arrays, the alias documents intent.
Vec2 = np.ndarray  # shape (2,): [x, y]
Vec3 = np.ndarray  # shape (3,): [x, y, z]


def vec3_rotate_x(v: Vec3, angle: float) -> Vec3:
    """Rotate around the x-axis by ``angle`` radians (x stays fixed)."""
    return np.array(
        [
            v[0],
            v[1] * math.cos(angle) - v[2] * math.sin(angle),
            v[1] * math.sin(angle) + v[2] * math.cos(angle),
        ],
        dtype=np.float64,
    )


def vec3_rotate_y(v: Vec3, angle: float) -> Vec3:
    """Rotate around the y-axis by ``angle`` radians (y stays fixed).

    Note: this step's C uses ``x*cos - z*sin`` / ``x*sin + z*cos`` (the same
    sign pattern as the z rotation); the course revisits the sign convention
    in a later step. Kept exactly as this step's C has it.
    """
    return np.array(
        [
            v[0] * math.cos(angle) - v[2] * math.sin(angle),
            v[1],
            v[0] * math.sin(angle) + v[2] * math.cos(angle),
        ],
        dtype=np.float64,
    )


def vec3_rotate_z(v: Vec3, angle: float) -> Vec3:
    """Rotate around the z-axis by ``angle`` radians (z stays fixed)."""
    return np.array(
        [
            v[0] * math.cos(angle) - v[1] * math.sin(angle),
            v[0] * math.sin(angle) + v[1] * math.cos(angle),
            v[2],
        ],
        dtype=np.float64,
    )
