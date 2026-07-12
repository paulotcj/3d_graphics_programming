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

from vector import Vec3, Vec4, vec3_cross, vec3_dot, vec3_normalize, vec3_sub

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
    divide (x/w, y/w) is what makes far objects smaller, and that same w is
    reused for the z-buffer and perspective-correct texture interpolation.
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

    The original z (depth) lands in ``result.w`` thanks to the matrix's last
    row; dividing x, y, z by that w performs the perspective divide. The w
    itself is intentionally left untouched so later stages (z-buffer and
    perspective-correct texturing) can still read the pre-divide depth.
    """
    # multiply the projection matrix by our original vector
    result = mat4_mul_vec4(mat_proj, v)

    # perform perspective divide with original z-value that is now stored in w
    if result[3] != 0.0:
        result[0] /= result[3]
        result[1] /= result[3]
        result[2] /= result[3]
    return result


def mat4_look_at(eye: Vec3, target: Vec3, up: Vec3) -> Mat4:
    """Build the view matrix from a camera position looking at a target point.

    Computes the camera's orthonormal basis — forward (z), right (x), and
    up (y) — then packs the basis rows together with a translation that
    moves the eye to the origin:

    | x.x   x.y   x.z  -dot(x,eye) |
    | y.x   y.y   y.z  -dot(y,eye) |
    | z.x   z.y   z.z  -dot(z,eye) |
    |   0     0     0            1 |

    Multiplying a world-space point by this matrix expresses it in camera
    space, where the camera sits at the origin looking down +z.
    """
    # Compute the forward (z), right (x), and up (y) vectors
    z = vec3_sub(target, eye)
    vec3_normalize(z)
    x = vec3_cross(up, z)
    vec3_normalize(x)
    y = vec3_cross(z, x)

    view_matrix = np.array(
        [
            [x[0], x[1], x[2], -vec3_dot(x, eye)],
            [y[0], y[1], y[2], -vec3_dot(y, eye)],
            [z[0], z[1], z[2], -vec3_dot(z, eye)],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    return view_matrix
