"""vector.py — mirrors src/vector.c / src/vector.h of C step 10.

The C step introduces the two vector types the whole renderer will be built
on:

    typedef struct { float x, y; }    vec2_t;
    typedef struct { float x, y, z; } vec3_t;

(vector.c itself is still empty — the math functions arrive in later steps.)

In this conversion a vector is a small NumPy ``float64`` array, so the C
struct fields map to indices: ``v.x`` -> ``v[0]``, ``v.y`` -> ``v[1]``,
``v.z`` -> ``v[2]``. The aliases below only document intent — both are plain
``np.ndarray`` at runtime.
"""

from __future__ import annotations

import numpy as np

Vec2 = np.ndarray  # shape (2,): [x, y]
Vec3 = np.ndarray  # shape (3,): [x, y, z]


def vec2_new(x: float, y: float) -> Vec2:
    """Create a 2D vector (C: a vec2_t compound literal)."""
    return np.array([x, y], dtype=np.float64)


def vec3_new(x: float, y: float, z: float) -> Vec3:
    """Create a 3D vector (C: a vec3_t compound literal)."""
    return np.array([x, y, z], dtype=np.float64)
