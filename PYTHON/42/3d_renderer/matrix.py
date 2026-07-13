"""matrix.py — mirrors src/matrix.c.

4x4 transformation matrices, represented as NumPy ``(4, 4)`` ``float64``
arrays in **row-major** layout with **column vectors**, exactly like the C
code:

    result = M @ v          # mat4_mul_vec4(m, v): row i of M dotted with v
    combined = A @ B        # mat4_mul_mat4(a, b): apply B first, then A

Because vectors are columns, transforms compose right-to-left — the C
comment "[T]*[R]*[S]*v" means scale happens first, translation last.
"""

from __future__ import annotations

import math

import numpy as np

from vector import Vec4

Mat4 = np.ndarray  # shape (4, 4), row-major


def mat4_identity() -> Mat4:
    """| 1 0 0 0 |
    | 0 1 0 0 |
    | 0 0 1 0 |
    | 0 0 0 1 |
    """
    return np.identity(4, dtype=np.float64)


def mat4_make_scale(sx: float, sy: float, sz: float) -> Mat4:
    """| sx  0  0  0 |
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
    """| 1  0  0  tx |
    | 0  1  0  ty |
    | 0  0  1  tz |
    | 0  0  0  1  |

    The translation lives in the last *column* because we multiply column
    vectors on the right: (M @ v).x = x + tx * w, and points carry w = 1.
    """
    m = mat4_identity()
    m[0, 3] = tx
    m[1, 3] = ty
    m[2, 3] = tz
    return m


def mat4_make_rotation_x(angle: float) -> Mat4:
    """Rotation around the x-axis by ``angle`` radians.

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
    """Rotation around the y-axis by ``angle`` radians.

    |  c  0  s  0 |
    |  0  1  0  0 |
    | -s  0  c  0 |
    |  0  0  0  1 |
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
    """Rotation around the z-axis by ``angle`` radians.

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
    """Multiply matrix by column vector: result_i = row_i(m) . v."""
    return m @ v


def mat4_mul_mat4(a: Mat4, b: Mat4) -> Mat4:
    """Matrix product a*b — the combined transform applies b first, then a."""
    return a @ b


def mat4_make_perspective(fov: float, aspect: float, znear: float, zfar: float) -> Mat4:
    """Build the perspective projection matrix.

    | (h/w)*1/tan(fov/2)             0              0                 0 |
    |                  0  1/tan(fov/2)              0                 0 |
    |                  0             0     zf/(zf-zn)  (-zf*zn)/(zf-zn) |
    |                  0             0              1                 0 |

    The last row copies the camera-space z into the output w component, so
    after this multiply ``w`` holds the original depth. The perspective
    divide (x/w, y/w) is what makes far objects smaller, and — new in this
    step — that same w is reused for perspective-correct texture
    interpolation in triangle.py.
    """
    m = np.zeros((4, 4), dtype=np.float64)
    m[0, 0] = aspect * (1 / math.tan(fov / 2))
    m[1, 1] = 1 / math.tan(fov / 2)
    m[2, 2] = zfar / (zfar - znear)
    m[2, 3] = (-zfar * znear) / (zfar - znear)
    m[3, 2] = 1.0
    return m


def mat4_mul_vec4_project(mat_proj: Mat4, v: Vec4) -> Vec4:
    """Project a vertex: multiply by the projection matrix, then perspective-divide.

    After the multiply, ``w`` holds the original camera-space depth; dividing
    x, y, z by it performs the perspective divide. ``w`` itself is left
    untouched so later stages can still use the true depth.
    """
    # multiply the projection matrix by our original vector
    result = mat4_mul_vec4(mat_proj, v)

    # perform perspective divide with original z-value that is now stored in w
    if result[3] != 0.0:
        result[0] /= result[3]
        result[1] /= result[3]
        result[2] /= result[3]

    return result
