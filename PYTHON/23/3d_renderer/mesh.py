"""mesh.py — mirrors src/mesh.c.

This is the step where the renderer starts reading geometry from disk: the
new ``load_obj_file_data()`` parses a Wavefront ``.obj`` file — ``v`` lines
into vertices and ``f v/vt/vn`` lines into faces (only the vertex indices
are kept; texture/normal indices are parsed and discarded, exactly like the
C ``sscanf``). The hard-coded cube data and ``load_cube_mesh_data()`` remain
from step 21 (the C keeps them too, just no longer calls them from setup).

In Python the dynamic arrays are plain ``list`` objects (CONVENTIONS.md §2:
``array.c`` is never ported), and ``mesh_t`` is a dataclass with the same
field names as the C struct.

Missing-asset fallback (CONVENTIONS.md §8): the original course repository
never committed the ``.obj`` model files. ``assets/cube.obj`` here is
generated from the hard-coded cube tables below so the parser is genuinely
exercised; if the requested file is missing anyway, a one-line warning is
printed and the built-in cube is loaded instead (the C would crash on the
NULL ``FILE*``). Drop the original course ``.obj`` files into ``assets/``
to see the real models.
"""

from __future__ import annotations

import os
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


def load_obj_file_data(filename: str) -> None:
    """Read a Wavefront .obj file and fill the global mesh (C: load_obj_file_data).

    Supports exactly the subset this step's C ``sscanf`` parser supports:

    - ``v x y z``                      — vertex positions.
    - ``f v/vt/vn v/vt/vn v/vt/vn``    — triangular faces; only the (1-based)
      vertex indices are kept, the texture/normal indices are read and
      discarded, just like the C code.

    §8 fallback: the C calls ``fopen`` without checking for NULL and would
    crash on a missing file; here we print a one-line warning and load the
    built-in cube instead.
    """
    if not os.path.isfile(filename):
        print(f"Warning: '{filename}' not found -- falling back to the built-in cube mesh.")
        load_cube_mesh_data()
        return

    with open(filename, "r", encoding="utf-8") as file:
        # C: while (fgets(line, 1024, file))
        for line in file:
            # Vertex information
            if line.startswith("v "):
                parts = line.split()
                vertex = vec3_new(float(parts[1]), float(parts[2]), float(parts[3]))
                mesh.vertices.append(vertex)

            # Face information
            if line.startswith("f "):
                vertex_indices: list[int] = []
                for corner in line.split()[1:4]:
                    # C: sscanf "%d/%d/%d" — vertex/texture/normal indices;
                    # only the vertex index is used at this step.
                    indices = corner.split("/")
                    vertex_indices.append(int(indices[0]))

                face = face_t(
                    a=vertex_indices[0],
                    b=vertex_indices[1],
                    c=vertex_indices[2],
                )

                mesh.faces.append(face)
