"""mesh.py — mirrors src/mesh.c.

Owns the global ``mesh`` (vertices, faces, and its scale / rotation /
translation transform), the hard-coded cube data, and the OBJ file loader.

The C dynamic arrays (array.c ``array_push``) become plain Python lists —
that is the whole reason array.c is never ported (CONVENTIONS.md §2).

Missing-asset fallback (CONVENTIONS.md §8): the original course repository
never committed the .obj model files, so if ``load_obj_file_data`` cannot
find the requested file it prints a one-line warning and loads the built-in
cube instead. Drop the original course .obj files into ``assets/`` to see
the real models.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from triangle import face_t
from vector import Vec3, vec3_new

N_CUBE_VERTICES: int = 8
N_CUBE_FACES: int = 6 * 2  # 6 cube faces, 2 triangles per face


@dataclass
class mesh_t:
    """A dynamic-size mesh: vertices, faces, and its transform values."""

    vertices: list[Vec3] = field(default_factory=list)  # dynamic array of vertices
    faces: list[face_t] = field(default_factory=list)  # dynamic array of faces
    rotation: Vec3 = field(default_factory=lambda: vec3_new(0, 0, 0))
    scale: Vec3 = field(default_factory=lambda: vec3_new(1.0, 1.0, 1.0))
    translation: Vec3 = field(default_factory=lambda: vec3_new(0, 0, 0))


# The global mesh — mirrors the `mesh_t mesh` global in mesh.c.
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
    face_t(a=1, b=2, c=3, color=0xFFFFFFFF),
    face_t(a=1, b=3, c=4, color=0xFFFFFFFF),
    # right
    face_t(a=4, b=3, c=5, color=0xFFFFFFFF),
    face_t(a=4, b=5, c=6, color=0xFFFFFFFF),
    # back
    face_t(a=6, b=5, c=7, color=0xFFFFFFFF),
    face_t(a=6, b=7, c=8, color=0xFFFFFFFF),
    # left
    face_t(a=8, b=7, c=2, color=0xFFFFFFFF),
    face_t(a=8, b=2, c=1, color=0xFFFFFFFF),
    # top
    face_t(a=2, b=7, c=5, color=0xFFFFFFFF),
    face_t(a=2, b=5, c=3, color=0xFFFFFFFF),
    # bottom
    face_t(a=6, b=8, c=1, color=0xFFFFFFFF),
    face_t(a=6, b=1, c=4, color=0xFFFFFFFF),
]


def load_cube_mesh_data() -> None:
    """Fill the global mesh with the hard-coded cube vertices and faces."""
    for cube_vertex in cube_vertices:
        mesh.vertices.append(cube_vertex)
    for cube_face in cube_faces:
        mesh.faces.append(cube_face)


def load_obj_file_data(filename: str) -> None:
    """Read vertex and face data from an OBJ file into the global mesh.

    Supports the exact subset the C parser reads at this step: ``v x y z``
    vertex lines and ``f a/at/an b/bt/bn c/ct/cn`` face lines (only the
    vertex indices are kept). Face colors are white — a readability
    improvement over the C code, whose designated initializer leaves the
    obj-face color zero-filled (0x00000000, i.e. black fills).

    Falls back to the built-in cube when the file is missing (§8) — the C
    code would crash on the NULL FILE*.
    """
    if not os.path.isfile(filename):
        print(f"Warning: '{filename}' not found - falling back to the built-in cube mesh.")
        load_cube_mesh_data()
        return

    with open(filename, "r", encoding="ascii", errors="replace") as file:
        for line in file:
            # Vertex information
            if line.startswith("v "):
                _, x, y, z = line.split()[:4]
                mesh.vertices.append(vec3_new(float(x), float(y), float(z)))
            # Face information
            if line.startswith("f "):
                # Each corner is "vertex/texture/normal"; keep the vertex index.
                corners = line.split()[1:4]
                vertex_indices = [int(corner.split("/")[0]) for corner in corners]
                face = face_t(
                    a=vertex_indices[0],
                    b=vertex_indices[1],
                    c=vertex_indices[2],
                )
                mesh.faces.append(face)
