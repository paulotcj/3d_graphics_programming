"""mesh.py — mirrors src/mesh.c (array.c's dynamic arrays become Python lists).

Owns the single global mesh: its vertices, faces, and the per-frame scale /
rotation / translation state, plus the two loaders — the hard-coded cube and
the OBJ file parser.

Missing-asset fallback (CONVENTIONS.md §8): the original course repository
never committed the .obj model files, so ``load_obj_file_data`` prints a
warning and falls back to the built-in cube (the same 8-vertex/12-face cube
from mesh.c, including its UVs) when the requested file does not exist —
first by parsing the generated ``assets/cube.obj`` (so the OBJ parser is
still genuinely exercised), and only if that is also gone, from the
hard-coded tables below. Drop the original course .obj files into
``assets/`` to see the real models.

Performance (CONVENTIONS.md §5): after loading, ``mesh_homogeneous_vertices``
caches all vertices as one ``(N, 4)`` NumPy array (w = 1 appended) so main.py
can transform the whole mesh with a single matmul per frame instead of C's
per-face-per-vertex ``mat4_mul_vec4`` — a documented, deliberate improvement.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import numpy as np

from texture import tex2_t
from triangle import face_t
from vector import Vec3

N_CUBE_VERTICES = 8
N_CUBE_FACES = 6 * 2  # 6 cube faces, 2 triangles per face

# Directory of this file — the §8 fallback cube.obj is resolved against it,
# never against the current working directory (CONVENTIONS.md §7).
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


###############################################################################
# Define a struct for dynamic size meshes, with array of vertices and faces
###############################################################################
@dataclass
class mesh_t:
    """A dynamic mesh: geometry plus its current transform state."""

    vertices: list[Vec3] = field(default_factory=list)  # dynamic array of vertices
    faces: list[face_t] = field(default_factory=list)  # dynamic array of faces
    rotation: Vec3 = field(default_factory=lambda: np.zeros(3))  # rotation x, y, z
    scale: Vec3 = field(default_factory=lambda: np.ones(3))  # scale x, y, z
    translation: Vec3 = field(default_factory=lambda: np.zeros(3))  # translation x, y, z


# Module-level state — mirrors the global `mesh_t mesh` in mesh.c.
mesh = mesh_t(
    vertices=[],
    faces=[],
    rotation=np.array([0.0, 0.0, 0.0]),
    scale=np.array([1.0, 1.0, 1.0]),
    translation=np.array([0.0, 0.0, 0.0]),
)

# (N, 4) float64 cache of mesh.vertices in homogeneous coordinates, built once
# after loading so main.py can batch-transform the whole mesh with one matmul
# per frame (CONVENTIONS.md §5). The vertex positions never change at runtime —
# only the world matrix does.
mesh_homogeneous_vertices: np.ndarray = np.zeros((0, 4))

cube_vertices: list[Vec3] = [
    np.array([-1.0, -1.0, -1.0]),  # 1
    np.array([-1.0, 1.0, -1.0]),  # 2
    np.array([1.0, 1.0, -1.0]),  # 3
    np.array([1.0, -1.0, -1.0]),  # 4
    np.array([1.0, 1.0, 1.0]),  # 5
    np.array([1.0, -1.0, 1.0]),  # 6
    np.array([-1.0, 1.0, 1.0]),  # 7
    np.array([-1.0, -1.0, 1.0]),  # 8
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


def _build_homogeneous_vertices() -> None:
    """Cache all mesh vertices as one (N, 4) array with w = 1 appended.

    Called once at the end of each loader; see the module docstring for why
    (one matmul per frame in main.py instead of a per-vertex Python loop).
    """
    global mesh_homogeneous_vertices
    mesh_homogeneous_vertices = np.hstack(
        [
            np.array(mesh.vertices, dtype=np.float64),
            np.ones((len(mesh.vertices), 1), dtype=np.float64),
        ]
    )


def load_cube_mesh_data() -> None:
    """Fill the global mesh with the hard-coded cube vertices and faces."""
    for i in range(N_CUBE_VERTICES):
        cube_vertex = cube_vertices[i]
        mesh.vertices.append(cube_vertex.copy())
    for i in range(N_CUBE_FACES):
        cube_face = cube_faces[i]
        mesh.faces.append(cube_face)
    _build_homogeneous_vertices()


def load_obj_file_data(filename: str) -> None:
    """Read the vertices, texture coordinates, and faces of an OBJ file.

    Supports exactly the subset the C parser reads with sscanf: ``v x y z``
    lines, ``vt u v`` lines, and ``f v/vt/vn v/vt/vn v/vt/vn`` faces (normal
    indices are read but unused).

    §8 fallback: if the file is missing, warn and load the built-in cube —
    via the generated ``assets/cube.obj`` when available (so the parser is
    still exercised), else from the hard-coded tables above.
    """
    if not os.path.isfile(filename):
        print(f"Warning: mesh file {filename} not found — falling back to the built-in cube mesh.")
        fallback_obj = os.path.join(_MODULE_DIR, "assets", "cube.obj")
        if os.path.isfile(fallback_obj):
            _parse_obj_file(fallback_obj)
            _build_homogeneous_vertices()
        else:
            load_cube_mesh_data()
        return

    _parse_obj_file(filename)
    _build_homogeneous_vertices()


def _parse_obj_file(filename: str) -> None:
    """Parse one OBJ file into the global mesh (the body of the C while loop)."""
    texcoords: list[tex2_t] = []

    with open(filename, "r", encoding="utf-8") as file:
        for line in file:
            # Vertex information
            if line.startswith("v "):
                parts = line.split()
                vertex = np.array([float(parts[1]), float(parts[2]), float(parts[3])])
                mesh.vertices.append(vertex)
            # Texture coordinate information
            if line.startswith("vt "):
                parts = line.split()
                texcoord = tex2_t(u=float(parts[1]), v=float(parts[2]))
                texcoords.append(texcoord)
            # Face information
            if line.startswith("f "):
                tokens = line.split()[1:4]
                vertex_indices = [int(token.split("/")[0]) for token in tokens]
                texture_indices = [int(token.split("/")[1]) for token in tokens]
                face = face_t(
                    a=vertex_indices[0],
                    b=vertex_indices[1],
                    c=vertex_indices[2],
                    a_uv=texcoords[texture_indices[0] - 1],
                    b_uv=texcoords[texture_indices[1] - 1],
                    c_uv=texcoords[texture_indices[2] - 1],
                    color=0xFFFFFFFF,
                )
                mesh.faces.append(face)
