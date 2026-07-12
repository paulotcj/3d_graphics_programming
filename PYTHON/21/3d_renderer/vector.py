"""vector.py — mirrors src/vector.c.

Owns the 2D/3D vector helpers used by the renderer at this step. A "vector"
in this conversion is a small NumPy ``float64`` array (length 2 or 3), so
the C struct fields map to indices: ``v.x`` -> ``v[0]``, ``v.y`` -> ``v[1]``,
``v.z`` -> ``v[2]``.

At step 21 the C file only contains the three Euler rotation helpers
(``vec3_rotate_x/y/z``); everything else (dot, cross, normalize, vec4, ...)
arrives in later steps. The ``vec2_new`` / ``vec3_new`` constructors below
stand in for C struct-literal initialization (``(vec3_t){ .x = ..., ... }``).
"""

from __future__ import annotations

import math

import numpy as np

# Type aliases: both are plain NumPy arrays, the alias documents intent.
Vec2 = np.ndarray  # shape (2,): [x, y]
Vec3 = np.ndarray  # shape (3,): [x, y, z]


def vec2_new(x: float, y: float) -> Vec2:
    """Create a new 2D vector (mirrors a C ``vec2_t`` struct literal)."""
    return np.array([x, y], dtype=np.float64)


def vec3_new(x: float, y: float, z: float) -> Vec3:
    """Create a new 3D vector (mirrors a C ``vec3_t`` struct literal)."""
    return np.array([x, y, z], dtype=np.float64)


def vec3_rotate_x(v: Vec3, angle: float) -> Vec3:
    """Rotate a vector around the X axis by ``angle`` radians.

    Standard 2D rotation applied to the (y, z) plane; x is unchanged:
        y' = y*cos(a) - z*sin(a)
        z' = y*sin(a) + z*cos(a)
    """
    return np.array(
        [
            v[0],
            v[1] * math.cos(angle) - v[2] * math.sin(angle),
            v[1] * math.sin(angle) + v[2] * math.cos(angle),
        ],
        dtype=np.float64,
    )


def vec3_rotate_y(v: Vec3, angle: float) -> Vec3:
    """Rotate a vector around the Y axis by ``angle`` radians.

    Rotation in the (x, z) plane; y is unchanged:
        x' = x*cos(a) - z*sin(a)
        z' = x*sin(a) + z*cos(a)
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
    """Rotate a vector around the Z axis by ``angle`` radians.

    Rotation in the (x, y) plane; z is unchanged:
        x' = x*cos(a) - y*sin(a)
        y' = x*sin(a) + y*cos(a)
    """
    return np.array(
        [
            v[0] * math.cos(angle) - v[1] * math.sin(angle),
            v[0] * math.sin(angle) + v[1] * math.cos(angle),
            v[2],
        ],
        dtype=np.float64,
    )
