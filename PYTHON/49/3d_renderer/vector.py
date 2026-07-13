"""vector.py — mirrors src/vector.c.

Owns the 2D/3D/4D vector helpers used across the renderer. A "vector" in this
conversion is a small NumPy ``float64`` array (length 2, 3, or 4), so the C
struct fields map to indices: ``v.x`` -> ``v[0]``, ``v.y`` -> ``v[1]``,
``v.z`` -> ``v[2]``, ``v.w`` -> ``v[3]``.

The function names, signatures, and math are 1:1 with the C file so both can
be read side by side. These scalar helpers are kept for readability; the hot
per-pixel paths in triangle.py and the per-mesh vertex transform in main.py
use NumPy array arithmetic directly instead (see CONVENTIONS.md §5).
"""

from __future__ import annotations

import math

import numpy as np

# Type aliases: all three are plain NumPy arrays, the alias documents intent.
Vec2 = np.ndarray  # shape (2,): [x, y]
Vec3 = np.ndarray  # shape (3,): [x, y, z]
Vec4 = np.ndarray  # shape (4,): [x, y, z, w]


###############################################################################
# Vector 2 functions
###############################################################################
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


def vec2_normalize(v: Vec2) -> None:
    """Normalize *in place* (mirrors the C pointer-mutating version)."""
    length = math.sqrt(v[0] * v[0] + v[1] * v[1])
    v /= length


###############################################################################
# Vector 3 functions
###############################################################################
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
    """Rotate around the y-axis by ``angle`` radians."""
    return np.array(
        [
            v[0] * math.cos(angle) + v[2] * math.sin(angle),
            v[1],
            -v[0] * math.sin(angle) + v[2] * math.cos(angle),
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


###############################################################################
# Vector conversion functions
###############################################################################
def vec4_from_vec3(v: Vec3) -> Vec4:
    """Promote to homogeneous coordinates with w = 1 (a *point*, not a direction)."""
    return np.array([v[0], v[1], v[2], 1.0], dtype=np.float64)


def vec3_from_vec4(v: Vec4) -> Vec3:
    """Drop the w component (copy, so mutating the result is safe)."""
    return np.array([v[0], v[1], v[2]], dtype=np.float64)


def vec2_from_vec4(v: Vec4) -> Vec2:
    """Keep only the screen-space x and y components."""
    return np.array([v[0], v[1]], dtype=np.float64)
