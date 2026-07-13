"""mesh.py — mirrors src/mesh.c / src/mesh.h of C step 18.

The hard-coded cube mesh: 8 corner vertices and 12 triangular faces (two per
cube side). Faces reference vertices by **1-based index** — the same
convention .obj files use, which pays off when OBJ loading arrives in
step 22.

Winding order matters later: looking at the cube from outside, every face
lists its vertices clockwise. Backface culling (step 25) relies on this.
"""

from __future__ import annotations

import numpy as np

from triangle import face_t
from vector import Vec3


def _v(x: float, y: float, z: float) -> Vec3:
    """Build a vertex (C: a vec3_t literal; vec3_new arrives in a later step)."""
    return np.array([x, y, z], dtype=np.float64)


N_MESH_VERTICES: int = 8
N_MESH_FACES: int = 6 * 2  # 6 cube sides, 2 triangles per side

# Points in the 3D space (C: vec3_t mesh_vertices[N_MESH_VERTICES])
mesh_vertices: list[Vec3] = [
    _v(-1, -1, -1),  # 1
    _v(-1,  1, -1),  # 2
    _v( 1,  1, -1),  # 3
    _v( 1, -1, -1),  # 4
    _v( 1,  1,  1),  # 5
    _v( 1, -1,  1),  # 6
    _v(-1,  1,  1),  # 7
    _v(-1, -1,  1),  # 8
]

# C: face_t mesh_faces[N_MESH_FACES] — 1-based vertex indexes
mesh_faces: list[face_t] = [
    # front
    face_t(a=1, b=2, c=3),
    face_t(a=1, b=3, c=4),
    # right
    face_t(a=4, b=3, c=5),
    face_t(a=4, b=5, c=6),
    # back
    face_t(a=6, b=5, c=7),
    face_t(a=6, b=7, c=8),
    # left
    face_t(a=8, b=7, c=2),
    face_t(a=8, b=2, c=1),
    # top
    face_t(a=2, b=7, c=5),
    face_t(a=2, b=5, c=3),
    # bottom
    face_t(a=6, b=8, c=1),
    face_t(a=6, b=1, c=4),
]
