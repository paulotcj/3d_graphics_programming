"""mesh.py — mirrors src/mesh.c.

Owns the single global mesh: its vertices, faces (with UV coordinates), and
the scale / rotation / translation used to build the world matrix each frame.
The C dynamic arrays (array.c) become plain Python lists.

Missing-asset fallback (CONVENTIONS.md §8): the original course repository
never committed the ``.obj`` model files. When ``load_obj_file_data`` is
asked for a file that does not exist it prints a one-line warning and loads
the built-in cube instead (the same hard-coded 8-vertex / 12-face cube the C
``mesh.c`` ships). Drop the original course ``.obj`` files into ``assets/``
to see the real models. (This step's C main calls ``load_cube_mesh_data``
directly anyway — the OBJ call is commented out, exactly as in main.c.)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from texture import tex2_t
from triangle import face_t
from vector import Vec3, vec3_new

N_CUBE_VERTICES: int = 8
N_CUBE_FACES: int = 6 * 2  # 6 cube faces, 2 triangles per face


@dataclass
class mesh_t:
    """The renderable mesh: geometry plus its transform in the world."""

    vertices: list[Vec3] = field(default_factory=list)  # dynamic array of vertices
    faces: list[face_t] = field(default_factory=list)  # dynamic array of faces
    rotation: Vec3 = field(default_factory=lambda: vec3_new(0, 0, 0))  # euler angles (x, y, z)
    scale: Vec3 = field(default_factory=lambda: vec3_new(1.0, 1.0, 1.0))
    translation: Vec3 = field(default_factory=lambda: vec3_new(0, 0, 0))


# Module-level state — mirrors the global `mesh_t mesh` in mesh.c.
mesh = mesh_t()

cube_vertices: list[Vec3] = [
    vec3_new(-1, -1, -1),  # 1
    vec3_new(-1,  1, -1),  # 2
    vec3_new( 1,  1, -1),  # 3
    vec3_new( 1, -1, -1),  # 4
    vec3_new( 1,  1,  1),  # 5
    vec3_new( 1, -1,  1),  # 6
    vec3_new(-1,  1,  1),  # 7
    vec3_new(-1, -1,  1),  # 8
]

# 1-based vertex indices + per-corner UV coordinates, exactly as in mesh.c.
cube_faces: list[face_t] = [
    # front
    face_t(a=1, b=2, c=3, a_uv=tex2_t(0, 0), b_uv=tex2_t(0, 1), c_uv=tex2_t(1, 1), color=0xFFFFFFFF),
    face_t(a=1, b=3, c=4, a_uv=tex2_t(0, 0), b_uv=tex2_t(1, 1), c_uv=tex2_t(1, 0), color=0xFFFFFFFF),
    # right
    face_t(a=4, b=3, c=5, a_uv=tex2_t(0, 0), b_uv=tex2_t(0, 1), c_uv=tex2_t(1, 1), color=0xFFFFFFFF),
    face_t(a=4, b=5, c=6, a_uv=tex2_t(0, 0), b_uv=tex2_t(1, 1), c_uv=tex2_t(1, 0), color=0xFFFFFFFF),
    # back
    face_t(a=6, b=5, c=7, a_uv=tex2_t(0, 0), b_uv=tex2_t(0, 1), c_uv=tex2_t(1, 1), color=0xFFFFFFFF),
    face_t(a=6, b=7, c=8, a_uv=tex2_t(0, 0), b_uv=tex2_t(1, 1), c_uv=tex2_t(1, 0), color=0xFFFFFFFF),
    # left
    face_t(a=8, b=7, c=2, a_uv=tex2_t(0, 0), b_uv=tex2_t(0, 1), c_uv=tex2_t(1, 1), color=0xFFFFFFFF),
    face_t(a=8, b=2, c=1, a_uv=tex2_t(0, 0), b_uv=tex2_t(1, 1), c_uv=tex2_t(1, 0), color=0xFFFFFFFF),
    # top
    face_t(a=2, b=7, c=5, a_uv=tex2_t(0, 0), b_uv=tex2_t(0, 1), c_uv=tex2_t(1, 1), color=0xFFFFFFFF),
    face_t(a=2, b=5, c=3, a_uv=tex2_t(0, 0), b_uv=tex2_t(1, 1), c_uv=tex2_t(1, 0), color=0xFFFFFFFF),
    # bottom
    face_t(a=6, b=8, c=1, a_uv=tex2_t(0, 0), b_uv=tex2_t(0, 1), c_uv=tex2_t(1, 1), color=0xFFFFFFFF),
    face_t(a=6, b=1, c=4, a_uv=tex2_t(0, 0), b_uv=tex2_t(1, 1), c_uv=tex2_t(1, 0), color=0xFFFFFFFF),
]


def load_cube_mesh_data() -> None:
    """Fill the global mesh with the hard-coded cube vertices and faces."""
    for cube_vertex in cube_vertices:
        mesh.vertices.append(cube_vertex.copy())
    for cube_face in cube_faces:
        # Copy the face so animating one run never mutates the template table.
        mesh.faces.append(
            face_t(
                a=cube_face.a, b=cube_face.b, c=cube_face.c,
                a_uv=tex2_t(cube_face.a_uv.u, cube_face.a_uv.v),
                b_uv=tex2_t(cube_face.b_uv.u, cube_face.b_uv.v),
                c_uv=tex2_t(cube_face.c_uv.u, cube_face.c_uv.v),
                color=cube_face.color,
            )
        )


def load_obj_file_data(filename: str) -> None:
    """Load geometry from an OBJ file into the global mesh.

    Mirrors the C sscanf loop: only ``v x y z`` and ``f v/vt/vn ...`` lines
    are read, and — like the C code at this step — the texture/normal indices
    are parsed but discarded, so OBJ faces get the C's zero-initialized UVs
    (0, 0) and a white base color.

    §8 fallback: if the file is missing, warn and load the built-in cube.
    """
    if not os.path.isfile(filename):
        print(f"Warning: '{filename}' not found -- falling back to the built-in cube mesh.")
        load_cube_mesh_data()
        return

    with open(filename, "r", encoding="utf-8") as file:
        for line in file:
            # Vertex information — "v x y z"
            if line.startswith("v "):
                parts = line.split()
                mesh.vertices.append(vec3_new(float(parts[1]), float(parts[2]), float(parts[3])))
            # Face information — "f v/vt/vn v/vt/vn v/vt/vn"
            if line.startswith("f "):
                corners = line.split()[1:4]
                vertex_indices = [int(corner.split("/")[0]) for corner in corners]
                face = face_t(
                    a=vertex_indices[0],
                    b=vertex_indices[1],
                    c=vertex_indices[2],
                    a_uv=tex2_t(0, 0),  # C: unset struct fields zero-initialize
                    b_uv=tex2_t(0, 0),
                    c_uv=tex2_t(0, 0),
                    color=0xFFFFFFFF,
                )
                mesh.faces.append(face)
