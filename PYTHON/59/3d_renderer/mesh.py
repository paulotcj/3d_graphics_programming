"""mesh.py — mirrors src/mesh.c.

Owns the scene's array of meshes: OBJ geometry loading, PNG texture loading,
and the per-mesh scale / rotation / translation used to build each world
matrix. The C dynamic arrays (array.c) become plain Python lists.

Missing-asset fallback (CONVENTIONS.md §8): the original course repository
never committed the ``.obj`` model files, only the PNG textures. When an
``.obj`` file is missing this module prints a one-line warning and loads the
built-in cube instead — first by parsing the generated ``assets/cube.obj``
(so the OBJ parser is still genuinely exercised), and if even that file is
gone, from the hard-coded vertex/face tables below (the same 8-vertex /
12-face cube the course's earlier ``mesh.c`` shipped). Missing textures fall
back to ``assets/cube.png`` the same way. Drop the original course ``.obj``
files into ``assets/`` to see the real models.

Performance (CONVENTIONS.md §5): at load time each mesh also gets
``homogeneous_vertices``, an ``(N, 4)`` NumPy array of its vertices with
w = 1 appended. main.py transforms ALL vertices of a mesh with one matrix
multiply per frame instead of C's per-face-per-vertex ``mat4_mul_vec4`` —
a documented, deliberate improvement.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import numpy as np

from texture import load_png_texture, tex2_t, texture_t
from triangle import face_t
from vector import Vec3, vec3_new

MAX_NUM_MESHES: int = 100

# Directory of this file — asset paths are resolved against it, never against
# the current working directory (CONVENTIONS.md §7).
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


@dataclass
class mesh_t:
    """One renderable mesh: geometry, texture, and its transform in the world."""

    vertices: list[Vec3] = field(default_factory=list)  # mesh dynamic array of vertices
    faces: list[face_t] = field(default_factory=list)  # mesh dynamic array of faces
    texture: texture_t | None = None  # mesh PNG texture
    scale: Vec3 = field(default_factory=lambda: vec3_new(1, 1, 1))
    rotation: Vec3 = field(default_factory=lambda: vec3_new(0, 0, 0))
    translation: Vec3 = field(default_factory=lambda: vec3_new(0, 0, 0))
    # (N, 4) float64 cache of the vertices in homogeneous coordinates, built
    # once after loading so main.py can batch-transform with one matmul.
    homogeneous_vertices: np.ndarray = field(default_factory=lambda: np.zeros((0, 4)))


# Module-level state — mirrors `static mesh_t meshes[MAX_NUM_MESHES]` and
# `static int mesh_count` in mesh.c (a growable list needs no fixed capacity).
meshes: list[mesh_t] = []


###############################################################################
# Built-in cube — the hard-coded mesh from the course's earlier mesh.c,
# used as the §8 fallback when an .obj file is missing.
###############################################################################
N_CUBE_VERTICES: int = 8
N_CUBE_FACES: int = 6 * 2  # 6 cube faces, 2 triangles per face

_CUBE_VERTICES: list[tuple[float, float, float]] = [
    (-1, -1, -1),  # 1
    (-1,  1, -1),  # 2
    ( 1,  1, -1),  # 3
    ( 1, -1, -1),  # 4
    ( 1,  1,  1),  # 5
    ( 1, -1,  1),  # 6
    (-1,  1,  1),  # 7
    (-1, -1,  1),  # 8
]

# (a, b, c, a_uv, b_uv, c_uv) with 1-based vertex indices, exactly as in C.
_CUBE_FACES: list[tuple[int, int, int, tuple[float, float], tuple[float, float], tuple[float, float]]] = [
    # front
    (1, 2, 3, (0, 1), (0, 0), (1, 0)),
    (1, 3, 4, (0, 1), (1, 0), (1, 1)),
    # right
    (4, 3, 5, (0, 1), (0, 0), (1, 0)),
    (4, 5, 6, (0, 1), (1, 0), (1, 1)),
    # back
    (6, 5, 7, (0, 1), (0, 0), (1, 0)),
    (6, 7, 8, (0, 1), (1, 0), (1, 1)),
    # left
    (8, 7, 2, (0, 1), (0, 0), (1, 0)),
    (8, 2, 1, (0, 1), (1, 0), (1, 1)),
    # top
    (2, 7, 5, (0, 1), (0, 0), (1, 0)),
    (2, 5, 3, (0, 1), (1, 0), (1, 1)),
    # bottom
    (6, 8, 1, (0, 1), (0, 0), (1, 0)),
    (6, 1, 4, (0, 1), (1, 0), (1, 1)),
]


def _load_cube_mesh_data(mesh: mesh_t) -> None:
    """Fill a mesh with the hard-coded cube (last-resort §8 fallback)."""
    for x, y, z in _CUBE_VERTICES:
        mesh.vertices.append(vec3_new(x, y, z))
    for a, b, c, a_uv, b_uv, c_uv in _CUBE_FACES:
        mesh.faces.append(
            face_t(
                a=a, b=b, c=c,
                a_uv=tex2_t(*a_uv), b_uv=tex2_t(*b_uv), c_uv=tex2_t(*c_uv),
                color=0xFFFFFFFF,
            )
        )


def _parse_obj_file(mesh: mesh_t, obj_filename: str) -> None:
    """Parse the OBJ subset the C sscanf loop supports: ``v``, ``vt``, ``f v/vt/vn``."""
    texcoords: list[tex2_t] = []
    with open(obj_filename, "r", encoding="utf-8") as file:
        for line in file:
            # Vertex information — "v x y z"
            if line.startswith("v "):
                parts = line.split()
                mesh.vertices.append(vec3_new(float(parts[1]), float(parts[2]), float(parts[3])))
            # Texture coordinate information — "vt u v"
            if line.startswith("vt "):
                parts = line.split()
                texcoords.append(tex2_t(u=float(parts[1]), v=float(parts[2])))
            # Face information — "f v/vt/vn v/vt/vn v/vt/vn"
            if line.startswith("f "):
                corners = line.split()[1:4]
                vertex_indices: list[int] = []
                texture_indices: list[int] = []
                for corner in corners:
                    indices = corner.split("/")
                    vertex_indices.append(int(indices[0]))
                    texture_indices.append(int(indices[1]))
                mesh.faces.append(
                    face_t(
                        a=vertex_indices[0],
                        b=vertex_indices[1],
                        c=vertex_indices[2],
                        a_uv=texcoords[texture_indices[0] - 1],
                        b_uv=texcoords[texture_indices[1] - 1],
                        c_uv=texcoords[texture_indices[2] - 1],
                        color=0xFFFFFFFF,
                    )
                )


def load_mesh_obj_data(mesh: mesh_t, obj_filename: str) -> None:
    """Load geometry from an OBJ file into the mesh (mirrors load_mesh_obj_data).

    §8 fallback: if the file is missing, warn and load the built-in cube —
    via the generated ``assets/cube.obj`` when available (so the parser is
    still exercised), else from the hard-coded tables.
    """
    if os.path.isfile(obj_filename):
        _parse_obj_file(mesh, obj_filename)
        return

    print(f"Warning: '{obj_filename}' not found -- falling back to the built-in cube mesh.")
    fallback_obj = os.path.join(_MODULE_DIR, "assets", "cube.obj")
    if os.path.isfile(fallback_obj):
        _parse_obj_file(mesh, fallback_obj)
    else:
        _load_cube_mesh_data(mesh)


def load_mesh_png_data(mesh: mesh_t, png_filename: str) -> None:
    """Load the mesh texture from a PNG file (mirrors load_mesh_png_data).

    §8 fallback: if the PNG cannot be loaded, warn and try ``assets/cube.png``.
    """
    texture = load_png_texture(png_filename)
    if texture is None:
        print(f"Warning: '{png_filename}' not found -- falling back to cube.png.")
        texture = load_png_texture(os.path.join(_MODULE_DIR, "assets", "cube.png"))
    if texture is not None:
        mesh.texture = texture


def load_mesh(
    obj_filename: str,
    png_filename: str,
    scale: Vec3,
    translation: Vec3,
    rotation: Vec3,
) -> None:
    """Load one mesh (geometry + texture) and register it in the scene."""
    mesh = mesh_t()
    load_mesh_obj_data(mesh, obj_filename)
    load_mesh_png_data(mesh, png_filename)

    mesh.scale = scale
    mesh.translation = translation
    mesh.rotation = rotation

    # Cache all vertices as one (N, 4) homogeneous array so main.py can
    # transform the whole mesh with a single matmul per frame (see module
    # docstring). The vertex positions never change — only the transform does.
    mesh.homogeneous_vertices = np.hstack(
        [
            np.array(mesh.vertices, dtype=np.float64),
            np.ones((len(mesh.vertices), 1), dtype=np.float64),
        ]
    )

    meshes.append(mesh)


def get_mesh(mesh_index: int) -> mesh_t:
    """Return the mesh at the given index."""
    return meshes[mesh_index]


def get_num_meshes() -> int:
    """Return how many meshes were loaded into the scene."""
    return len(meshes)


def rotate_mesh_x(mesh_index: int, angle: float) -> None:
    """Add to a mesh's rotation around the x-axis."""
    meshes[mesh_index].rotation[0] += angle


def rotate_mesh_y(mesh_index: int, angle: float) -> None:
    """Add to a mesh's rotation around the y-axis."""
    meshes[mesh_index].rotation[1] += angle


def rotate_mesh_z(mesh_index: int, angle: float) -> None:
    """Add to a mesh's rotation around the z-axis."""
    meshes[mesh_index].rotation[2] += angle


def free_meshes() -> None:
    """Release all meshes (C: array_free + upng_free; Python: clear the list)."""
    meshes.clear()
