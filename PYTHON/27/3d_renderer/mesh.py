"""mesh.py — mirrors src/mesh.c (step 27).

Owns the global ``mesh`` (vertices, faces, rotation), the hard-coded cube
data, and the OBJ file loader. The C file's dynamic ``array_push`` arrays
become plain Python lists (``array.c``/``array.h`` are never ported — see
CONVENTIONS.md §3).

Asset fallback (CONVENTIONS.md §8): the original course repository never
committed its ``.obj`` files, so if the requested file is missing we print a
one-line warning and load the built-in cube instead of crashing (the C code
would segfault on the NULL ``FILE*``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from triangle import face_t
from vector import Vec3, vec3_new

N_CUBE_VERTICES: int = 8
N_CUBE_FACES: int = 6 * 2  # 6 cube faces, 2 triangles per face


###############################################################################
# Define a class for dynamic size meshes, with array of vertices and faces
###############################################################################
@dataclass
class mesh_t:
    """A mesh: vertex list, face list, and its current Euler rotation."""

    vertices: list[Vec3] = field(default_factory=list)  # dynamic array of vertices
    faces: list[face_t] = field(default_factory=list)  # dynamic array of faces
    rotation: Vec3 = field(default_factory=lambda: vec3_new(0, 0, 0))  # x, y, z


mesh = mesh_t()

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
    """Fill the global mesh with the hard-coded cube vertices and faces."""
    for cube_vertex in cube_vertices:
        mesh.vertices.append(cube_vertex.copy())
    for cube_face in cube_faces:
        mesh.faces.append(face_t(a=cube_face.a, b=cube_face.b, c=cube_face.c))


def load_obj_file_data(filename: str) -> None:
    """Parse an OBJ file into the global mesh.

    Supports exactly what this step's C parser supports: ``v x y z`` vertex
    lines and ``f a/at/an b/bt/bn c/ct/cn`` face lines (only the vertex
    indices are kept — texture and normal indices are parsed and discarded,
    like the C sscanf).
    """
    if not os.path.isfile(filename):
        # CONVENTIONS.md §8: graceful fallback instead of the C segfault.
        print(f"Warning: could not open '{filename}' — falling back to the built-in cube mesh.")
        load_cube_mesh_data()
        return

    with open(filename, "r", encoding="ascii", errors="replace") as file:
        for line in file:
            # Vertex information
            if line.startswith("v "):
                parts = line.split()
                mesh.vertices.append(
                    vec3_new(float(parts[1]), float(parts[2]), float(parts[3]))
                )
            # Face information
            if line.startswith("f "):
                parts = line.split()
                vertex_indices = [int(part.split("/")[0]) for part in parts[1:4]]
                mesh.faces.append(
                    face_t(a=vertex_indices[0], b=vertex_indices[1], c=vertex_indices[2])
                )
