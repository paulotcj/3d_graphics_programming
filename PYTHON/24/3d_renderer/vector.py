"""vector.py — mirrors src/vector.c (step 24: the full vec2/vec3 math library).

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

###############################################################################
# Vector 2D functions (new in step 24)
###############################################################################
def vec2_length(v: Vec2) -> float:
    """Euclidean length sqrt(x^2 + y^2)."""
    return math.sqrt(v[0] * v[0] + v[1] * v[1])


def vec2_add(a: Vec2, b: Vec2) -> Vec2:
    """Component-wise a + b."""
    return np.array([a[0] + b[0], a[1] + b[1]], dtype=np.float64)


def vec2_sub(a: Vec2, b: Vec2) -> Vec2:
    """Component-wise a - b."""
    return np.array([a[0] - b[0], a[1] - b[1]], dtype=np.float64)


def vec2_mul(v: Vec2, factor: float) -> Vec2:
    """Scale a vector by a factor."""
    return np.array([v[0] * factor, v[1] * factor], dtype=np.float64)


def vec2_div(v: Vec2, factor: float) -> Vec2:
    """Divide a vector by a factor."""
    return np.array([v[0] / factor, v[1] / factor], dtype=np.float64)


def vec2_dot(a: Vec2, b: Vec2) -> float:
    """Dot product: how aligned two vectors are (a.x*b.x + a.y*b.y)."""
    return (a[0] * b[0]) + (a[1] * b[1])


###############################################################################
# Vector 3D functions (new in step 24)
###############################################################################
def vec3_length(v: Vec3) -> float:
    """Euclidean length sqrt(x^2 + y^2 + z^2)."""
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def vec3_add(a: Vec3, b: Vec3) -> Vec3:
    """Component-wise a + b."""
    return np.array([a[0] + b[0], a[1] + b[1], a[2] + b[2]], dtype=np.float64)


def vec3_sub(a: Vec3, b: Vec3) -> Vec3:
    """Component-wise a - b."""
    return np.array([a[0] - b[0], a[1] - b[1], a[2] - b[2]], dtype=np.float64)


def vec3_mul(v: Vec3, factor: float) -> Vec3:
    """Scale a vector by a factor."""
    return np.array([v[0] * factor, v[1] * factor, v[2] * factor], dtype=np.float64)


def vec3_div(v: Vec3, factor: float) -> Vec3:
    """Divide a vector by a factor."""
    return np.array([v[0] / factor, v[1] / factor, v[2] / factor], dtype=np.float64)


def vec3_cross(a: Vec3, b: Vec3) -> Vec3:
    """Cross product: the vector perpendicular to both a and b.

    Follows the right-hand-rule component formula; the winding of a and b
    decides which way the result points — this becomes the face normal used
    for backface culling in the next steps.
    """
    return np.array(
        [
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0],
        ],
        dtype=np.float64,
    )


def vec3_dot(a: Vec3, b: Vec3) -> float:
    """Dot product: positive when vectors point the same way, 0 when perpendicular."""
    return (a[0] * b[0]) + (a[1] * b[1]) + (a[2] * b[2])
