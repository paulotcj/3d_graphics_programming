"""vector.py — mirrors src/vector.c (step 27).

Owns the 2D/3D vector helpers used across the renderer. A "vector" in this
conversion is a small NumPy ``float64`` array (length 2 or 3), so the C
struct fields map to indices: ``v.x`` -> ``v[0]``, ``v.y`` -> ``v[1]``,
``v.z`` -> ``v[2]``.

The function names, signatures, and math are 1:1 with the C file so both can
be read side by side. At this step the C code has no vec4 / matrix functions
yet, so neither does this module.
"""

from __future__ import annotations

import math

import numpy as np

# Type aliases: both are plain NumPy arrays, the alias documents intent.
Vec2 = np.ndarray  # shape (2,): [x, y]
Vec3 = np.ndarray  # shape (3,): [x, y, z]


###############################################################################
# Vector 2 functions
###############################################################################
def vec2_new(x: float, y: float) -> Vec2:
    """Create a new 2D vector (C: a ``vec2_t`` struct literal)."""
    return np.array([x, y], dtype=np.float64)


def vec2_length(v: Vec2) -> float:
    """Return the Euclidean length sqrt(x^2 + y^2)."""
    return math.sqrt(v[0] * v[0] + v[1] * v[1])


def vec2_add(a: Vec2, b: Vec2) -> Vec2:
    """Component-wise addition a + b."""
    return a + b


def vec2_sub(a: Vec2, b: Vec2) -> Vec2:
    """Component-wise subtraction a - b."""
    return a - b


def vec2_mul(v: Vec2, factor: float) -> Vec2:
    """Scale a vector by a scalar factor."""
    return v * factor


def vec2_div(v: Vec2, factor: float) -> Vec2:
    """Divide a vector by a scalar factor."""
    return v / factor


def vec2_dot(a: Vec2, b: Vec2) -> float:
    """Dot product: how aligned two vectors are."""
    return float(a[0] * b[0] + a[1] * b[1])


def vec2_normalize(v: Vec2) -> None:
    """Normalize *in place* (mirrors the C pointer-mutating version)."""
    length = math.sqrt(v[0] * v[0] + v[1] * v[1])
    v /= length


###############################################################################
# Vector 3 functions
###############################################################################
def vec3_new(x: float, y: float, z: float) -> Vec3:
    """Create a new 3D vector (C: a ``vec3_t`` struct literal)."""
    return np.array([x, y, z], dtype=np.float64)


def vec3_length(v: Vec3) -> float:
    """Return the Euclidean length sqrt(x^2 + y^2 + z^2)."""
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def vec3_add(a: Vec3, b: Vec3) -> Vec3:
    """Component-wise addition a + b."""
    return a + b


def vec3_sub(a: Vec3, b: Vec3) -> Vec3:
    """Component-wise subtraction a - b."""
    return a - b


def vec3_mul(v: Vec3, factor: float) -> Vec3:
    """Scale a vector by a scalar factor."""
    return v * factor


def vec3_div(v: Vec3, factor: float) -> Vec3:
    """Divide a vector by a scalar factor."""
    return v / factor


def vec3_cross(a: Vec3, b: Vec3) -> Vec3:
    """Cross product: a vector perpendicular to both a and b.

    The sign follows the left-handed convention used throughout the course
    (positive z goes *into* the screen).
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
    """Dot product: |a||b|cos(angle) — positive when vectors point together."""
    return float(a[0] * b[0] + a[1] * b[1] + a[2] * b[2])


def vec3_normalize(v: Vec3) -> None:
    """Normalize *in place* to unit length (mirrors the C pointer version)."""
    length = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    v /= length


def vec3_rotate_x(v: Vec3, angle: float) -> Vec3:
    """Rotate around the x-axis by ``angle`` radians."""
    return np.array(
        [
            v[0],
            v[1] * math.cos(angle) - v[2] * math.sin(angle),
            v[1] * math.sin(angle) + v[2] * math.cos(angle),
        ],
        dtype=np.float64,
    )


def vec3_rotate_y(v: Vec3, angle: float) -> Vec3:
    """Rotate around the y-axis by ``angle`` radians.

    Note: this step's C code uses ``x*cos - z*sin`` / ``x*sin + z*cos``
    (the same sign pattern as the z rotation); the sign convention is
    revisited in later steps. We mirror the C exactly.
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
    """Rotate around the z-axis by ``angle`` radians."""
    return np.array(
        [
            v[0] * math.cos(angle) - v[1] * math.sin(angle),
            v[0] * math.sin(angle) + v[1] * math.cos(angle),
            v[2],
        ],
        dtype=np.float64,
    )
