"""mesh.py — mirrors src/mesh.c.

Owns the single global mesh (vertices, faces, and its scale / rotation /
translation), the hard-coded 8-vertex / 12-face cube, and the tiny OBJ
parser. The C dynamic arrays (array.c) become plain Python lists
(CONVENTIONS.md §2), so array_push -> list.append and array_length -> len.

Missing-asset fallback (CONVENTIONS.md §8): the original course repository
never committed the .obj model files, so if the requested file does not
exist ``load_obj_file_data`` prints a one-line warning and loads the
built-in cube instead of crashing. ``assets/cube.obj`` is shipped with this
step, so the OBJ parser is genuinely exercised by default.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from texture import tex2_t
from triangle import face_t
from vector import Vec3, vec3_new

N_CUBE_VERTICES = 8
N_CUBE_FACES = 6 * 2  # 6 cube faces, 2 triangles per face


###############################################################################
# Define a class for dynamic size meshes, with array of vertices and faces
###############################################################################
@dataclass
class mesh_t:
    """A mesh: vertex/face lists plus its transform (scale, rotation, translation)."""

    vertices: list[Vec3] = field(default_factory=list)  # dynamic array of vertices
    faces: list[face_t] = field(default_factory=list)  # dynamic array of faces
    rotation: Vec3 = field(default_factory=lambda: vec3_new(0, 0, 0))
    scale: Vec3 = field(default_factory=lambda: vec3_new(1.0, 1.0, 1.0))
    translation: Vec3 = field(default_factory=lambda: vec3_new(0, 0, 0))


# Module-level state — mirrors the `mesh_t mesh` global in mesh.c.
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
    face_t(a=1, b=2, c=3, a_uv=tex2_t(0, 1), b_uv=tex2_t(0, 0), c_uv=tex2_t(1, 0), color=0xFFFFFFFF),
    face_t(a=1, b=3, c=4, a_uv=tex2_t(0, 1), b_uv=tex2_t(1, 0), c_uv=tex2_t(1, 1), color=0xFFFFFFFF),
    # right
    face_t(a=4, b=3, c=5, a_uv=tex2_t(0, 1), b_uv=tex2_t(0, 0), c_uv=tex2_t(1, 0), color=0xFFFFFFFF),
    face_t(a=4, b=5, c=6, a_uv=tex2_t(0, 1), b_uv=tex2_t(1, 0), c_uv=tex2_t(1, 1), color=0xFFFFFFFF),
    # back
    face_t(a=6, b=5, c=7, a_uv=tex2_t(0, 1), b_uv=tex2_t(0, 0), c_uv=tex2_t(1, 0), color=0xFFFFFFFF),
    face_t(a=6, b=7, c=8, a_uv=tex2_t(0, 1), b_uv=tex2_t(1, 0), c_uv=tex2_t(1, 1), color=0xFFFFFFFF),
    # left
    face_t(a=8, b=7, c=2, a_uv=tex2_t(0, 1), b_uv=tex2_t(0, 0), c_uv=tex2_t(1, 0), color=0xFFFFFFFF),
    face_t(a=8, b=2, c=1, a_uv=tex2_t(0, 1), b_uv=tex2_t(1, 0), c_uv=tex2_t(1, 1), color=0xFFFFFFFF),
    # top
    face_t(a=2, b=7, c=5, a_uv=tex2_t(0, 1), b_uv=tex2_t(0, 0), c_uv=tex2_t(1, 0), color=0xFFFFFFFF),
    face_t(a=2, b=5, c=3, a_uv=tex2_t(0, 1), b_uv=tex2_t(1, 0), c_uv=tex2_t(1, 1), color=0xFFFFFFFF),
    # bottom
    face_t(a=6, b=8, c=1, a_uv=tex2_t(0, 1), b_uv=tex2_t(0, 0), c_uv=tex2_t(1, 0), color=0xFFFFFFFF),
    face_t(a=6, b=1, c=4, a_uv=tex2_t(0, 1), b_uv=tex2_t(1, 0), c_uv=tex2_t(1, 1), color=0xFFFFFFFF),
]


def load_cube_mesh_data() -> None:
    """Copy the hard-coded cube vertices and faces into the global mesh."""
    for cube_vertex in cube_vertices:
        mesh.vertices.append(cube_vertex.copy())
    for cube_face in cube_faces:
        mesh.faces.append(
            face_t(
                a=cube_face.a,
                b=cube_face.b,
                c=cube_face.c,
                a_uv=tex2_t(cube_face.a_uv.u, cube_face.a_uv.v),
                b_uv=tex2_t(cube_face.b_uv.u, cube_face.b_uv.v),
                c_uv=tex2_t(cube_face.c_uv.u, cube_face.c_uv.v),
                color=cube_face.color,
            )
        )


def load_obj_file_data(filename: str) -> None:
    """Read the vertices, texture coordinates, and faces of a Wavefront .obj.

    Supports exactly the subset the C parser reads for this step:
    ``v x y z``, ``vt u v``, and ``f v/vt/vn v/vt/vn v/vt/vn``.

    Missing-file fallback (CONVENTIONS.md §8): the course's .obj assets were
    never committed, so a missing file loads the built-in cube instead.
    """
    if not os.path.isfile(filename):
        print(f"Warning: '{filename}' not found — falling back to the built-in cube mesh.")
        load_cube_mesh_data()
        return

    texcoords: list[tex2_t] = []

    with open(filename, "r", encoding="ascii", errors="replace") as file:
        for line in file:
            # Vertex information
            if line.startswith("v "):
                _, x, y, z = line.split()[:4]
                mesh.vertices.append(vec3_new(float(x), float(y), float(z)))
            # Texture coordinate information
            if line.startswith("vt "):
                _, u, v = line.split()[:3]
                texcoords.append(tex2_t(float(u), float(v)))
            # Face information
            if line.startswith("f "):
                corners = line.split()[1:4]
                vertex_indices = []
                texture_indices = []
                for corner in corners:  # each corner is "v/vt/vn"
                    v_idx, vt_idx, _vn_idx = corner.split("/")
                    vertex_indices.append(int(v_idx))
                    texture_indices.append(int(vt_idx))
                face = face_t(
                    a=vertex_indices[0],
                    b=vertex_indices[1],
                    c=vertex_indices[2],
                    a_uv=tex2_t(texcoords[texture_indices[0] - 1].u, texcoords[texture_indices[0] - 1].v),
                    b_uv=tex2_t(texcoords[texture_indices[1] - 1].u, texcoords[texture_indices[1] - 1].v),
                    c_uv=tex2_t(texcoords[texture_indices[2] - 1].u, texcoords[texture_indices[2] - 1].v),
                    color=0xFFFFFFFF,
                )
                mesh.faces.append(face)
