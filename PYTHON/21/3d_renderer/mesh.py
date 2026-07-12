"""mesh.py — mirrors src/mesh.c.

This is the step where the mesh becomes a *dynamic* data structure: instead
of the fixed global ``mesh_vertices`` / ``mesh_faces`` arrays of step 20, the
C code introduces a ``mesh_t`` struct whose vertices and faces are growable
arrays (the course's ``array.c``), plus a per-mesh ``rotation``. The static
cube data is kept — renamed to ``cube_vertices`` / ``cube_faces`` — and
``load_cube_mesh_data()`` copies it into the dynamic mesh at startup.

In Python the dynamic arrays are plain ``list`` objects (CONVENTIONS.md §2:
``array.c`` is never ported), and ``mesh_t`` is a dataclass with the same
field names as the C struct.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from triangle import face_t
from vector import Vec3, vec3_new

N_CUBE_VERTICES: int = 8
N_CUBE_FACES: int = 6 * 2  # 6 cube faces, 2 triangles per face


###############################################################################
# Define a class for dynamic size meshes, with lists of vertices and faces
###############################################################################
@dataclass
class mesh_t:
    """Mirror of the C ``mesh_t``: dynamic vertices/faces plus a rotation."""

    vertices: list[Vec3] = field(default_factory=list)  # dynamic array of vertices
    faces: list[face_t] = field(default_factory=list)  # dynamic array of faces
    rotation: Vec3 = field(default_factory=lambda: vec3_new(0, 0, 0))


# The single global mesh the renderer works on (C: `mesh_t mesh = {...}`).
mesh = mesh_t()

# Hard-coded cube: 8 corner vertices of a 2x2x2 cube centered on the origin.
cube_vertices: list[Vec3] = [
    vec3_new(-1, -1, -1),  # 1
    vec3_new(-1, 1, -1),  # 2
    vec3_new(1, 1, -1),  # 3
    vec3_new(1, -1, -1),  # 4
    vec3_new(1, 1, 1),  # 5
    vec3_new(1, -1, 1),  # 6
    vec3_new(-1, 1, 1),  # 7
    vec3_new(-1, -1, 1),  # 8
]

# 12 triangles (2 per cube side), as 1-based indexes into cube_vertices.
cube_faces: list[face_t] = [
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


def load_cube_mesh_data() -> None:
    """Copy the static cube data into the dynamic mesh (C: array_push loops)."""
    for i in range(N_CUBE_VERTICES):
        cube_vertex = cube_vertices[i]
        mesh.vertices.append(cube_vertex)
    for i in range(N_CUBE_FACES):
        cube_face = cube_faces[i]
        mesh.faces.append(cube_face)
