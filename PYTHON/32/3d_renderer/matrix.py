"""matrix.py — mirrors src/matrix.c / src/matrix.h of C step 32.

First contact with 4x4 matrices. A ``mat4_t`` is a NumPy ``float64`` array of
shape (4, 4) — ``m.m[i][j]`` in C is ``m[i, j]`` here. This step only needs
three functions: the identity, a scale matrix, and matrix-times-vector.

Why 4x4 for 3D points? The extra **w** component (see vec4_from_vec3, w = 1)
is what lets a matrix express *translation* as well as rotation/scale — that
payoff arrives in the next step.
"""

from __future__ import annotations

import math

import numpy as np

Mat4 = np.ndarray  # shape (4, 4): row-major, m[row, col] == C m.m[row][col]

Vec4 = np.ndarray  # shape (4,): [x, y, z, w]


def mat4_identity() -> Mat4:
    """Return the 4x4 identity matrix.

    | 1 0 0 0 |
    | 0 1 0 0 |
    | 0 0 1 0 |
    | 0 0 0 1 |
    """
    return np.identity(4, dtype=np.float64)


def mat4_make_scale(sx: float, sy: float, sz: float) -> Mat4:
    """Return a scale matrix: the diagonal carries the scale factors.

    | sx  0  0  0 |
    |  0 sy  0  0 |
    |  0  0 sz  0 |
    |  0  0  0  1 |
    """
    m = mat4_identity()
    m[0, 0] = sx
    m[1, 1] = sy
    m[2, 2] = sz
    return m


def mat4_make_translation(tx: float, ty: float, tz: float) -> Mat4:
    """Return a translation matrix: the offsets live in the last column.

    | 1  0  0  tx |
    | 0  1  0  ty |
    | 0  0  1  tz |
    | 0  0  0  1  |

    This is the payoff of homogeneous coordinates: the vector's w = 1 picks
    up the last column, so multiplying MOVES the point — something a 3x3
    matrix can never do.
    """
    m = mat4_identity()
    m[0, 3] = tx
    m[1, 3] = ty
    m[2, 3] = tz
    return m


def mat4_make_rotation_x(angle: float) -> Mat4:
    """Rotation around the x axis: x is untouched, y/z mix by cos/sin.

    | 1  0  0  0 |
    | 0  c -s  0 |
    | 0  s  c  0 |
    | 0  0  0  1 |
    """
    c = math.cos(angle)
    s = math.sin(angle)
    m = mat4_identity()
    m[1, 1] = c
    m[1, 2] = -s
    m[2, 1] = s
    m[2, 2] = c
    return m


def mat4_make_rotation_y(angle: float) -> Mat4:
    """Rotation around the y axis. Note the flipped sign layout:

    |  c  0  s  0 |
    |  0  1  0  0 |
    | -s  0  c  0 |
    |  0  0  0  1 |

    The sign pattern differs from x/z so all three rotate the same
    (counter-clockwise) direction in a left-handed system.
    """
    c = math.cos(angle)
    s = math.sin(angle)
    m = mat4_identity()
    m[0, 0] = c
    m[0, 2] = s
    m[2, 0] = -s
    m[2, 2] = c
    return m


def mat4_make_rotation_z(angle: float) -> Mat4:
    """Rotation around the z axis: z untouched, x/y mix by cos/sin.

    | c -s  0  0 |
    | s  c  0  0 |
    | 0  0  1  0 |
    | 0  0  0  1 |
    """
    c = math.cos(angle)
    s = math.sin(angle)
    m = mat4_identity()
    m[0, 0] = c
    m[0, 1] = -s
    m[1, 0] = s
    m[1, 1] = c
    return m


def mat4_mul_vec4(m: Mat4, v: Vec4) -> Vec4:
    """Multiply a 4x4 matrix by a 4-component vector (C: four dot products).

    Each result component is the dot product of one matrix ROW with v —
    which is exactly what NumPy's ``m @ v`` computes in one call.
    """
    return m @ v
