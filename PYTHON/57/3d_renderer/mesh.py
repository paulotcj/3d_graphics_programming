"""mesh.py — mirrors src/mesh.c.

NEW in step 57: the renderer supports **multiple meshes**. The single global
``mesh`` is replaced by a static array of up to MAX_NUM_MESHES meshes, each
loaded with ``load_mesh(obj, png, scale, translation, rotation)`` and carrying
its **own texture** (``mesh_t.texture``). ``get_num_meshes`` / ``get_mesh``
expose the array to main.py's update loop.

The OBJ parser supports exactly the subset the C parser reads: ``v x y z``,
``vt u v``, and ``f v/vt/vn v/vt/vn v/vt/vn`` lines.

Missing-asset fallback (CONVENTIONS.md §8): the original course repository
never committed the ``.obj`` model files, so if the requested file does not
exist this module prints a one-line warning and loads the built-in cube
instead — first by parsing the generated ``assets/cube.obj`` (so the OBJ
parser is still genuinely exercised), and only if that is also gone, from
the classic hard-coded 8-vertex/12-face tables. Drop the original course
``.obj`` files into ``assets/`` to see the real models. Likewise a missing
PNG falls back to ``assets/cube.png``.

Replaced C helpers: ``array.c`` (dynamic arrays) becomes plain Python lists;
``upng.c`` (PNG decoding) is handled by texture.py via pygame.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import numpy as np

from texture import tex2_t, texture_t, load_png_texture
from triangle import face_t
from vector import Vec3, vec3_new

# The step directory, so asset paths like "./assets/f22.obj" work no matter
# which directory the program is launched from (CONVENTIONS.md §7).
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MAX_NUM_MESHES: int = 10


@dataclass
class mesh_t:
    """A mesh instance: geometry + texture + its own transform in the scene."""

    vertices: list[Vec3] = field(default_factory=list)  # mesh dynamic array of vertices
    faces: list[face_t] = field(default_factory=list)  # mesh dynamic array of faces
    texture: texture_t | None = None  # mesh PNG texture
    rotation: Vec3 = field(default_factory=lambda: vec3_new(0, 0, 0))
    scale: Vec3 = field(default_factory=lambda: vec3_new(1, 1, 1))
    translation: Vec3 = field(default_factory=lambda: vec3_new(0, 0, 0))

    # Performance improvement (CONVENTIONS.md §5): all vertices stacked as one
    # (N, 4) homogeneous array so main.py can transform the whole mesh with a
    # single matrix multiplication per frame instead of C's per-vertex loop.
    homogeneous_vertices: np.ndarray = field(default_factory=lambda: np.zeros((0, 4)))


# Module-level state — mirrors `static mesh_t meshes[MAX_NUM_MESHES]` and
# `static int mesh_count` in mesh.c.
meshes: list[mesh_t] = []


# The hard-coded cube from the earlier steps' mesh.c, used as the §8 fallback
# when an .obj file is missing (8 vertices, 6 faces x 2 triangles, with UVs).
_CUBE_VERTICES: list[tuple[float, float, float]] = [
    (-1, -1, -1),  # 1
    (-1, 1, -1),  # 2
    (1, 1, -1),  # 3
    (1, -1, -1),  # 4
    (1, 1, 1),  # 5
    (1, -1, 1),  # 6
    (-1, 1, 1),  # 7
    (-1, -1, 1),  # 8
]

# (a, b, c, a_uv, b_uv, c_uv, color) with 1-based vertex indices.
_CUBE_FACES: list[tuple[int, int, int, tuple, tuple, tuple, int]] = [
    # front
    (1, 2, 3, (0, 1), (0, 0), (1, 0), 0xFFFFFFFF),
    (1, 3, 4, (0, 1), (1, 0), (1, 1), 0xFFFFFFFF),
    # right
    (4, 3, 5, (0, 1), (0, 0), (1, 0), 0xFFFFFFFF),
    (4, 5, 6, (0, 1), (1, 0), (1, 1), 0xFFFFFFFF),
    # back
    (6, 5, 7, (0, 1), (0, 0), (1, 0), 0xFFFFFFFF),
    (6, 7, 8, (0, 1), (1, 0), (1, 1), 0xFFFFFFFF),
    # left
    (8, 7, 2, (0, 1), (0, 0), (1, 0), 0xFFFFFFFF),
    (8, 2, 1, (0, 1), (1, 0), (1, 1), 0xFFFFFFFF),
    # top
    (2, 7, 5, (0, 1), (0, 0), (1, 0), 0xFFFFFFFF),
    (2, 5, 3, (0, 1), (1, 0), (1, 1), 0xFFFFFFFF),
    # bottom
    (6, 8, 1, (0, 1), (0, 0), (1, 0), 0xFFFFFFFF),
    (6, 1, 4, (0, 1), (1, 0), (1, 1), 0xFFFFFFFF),
]


def _resolve_asset_path(filename: str) -> str:
    """Turn a C-style relative path ("./assets/f22.obj") into an absolute one."""
    return os.path.join(_BASE_DIR, filename.lstrip("./"))


def load_mesh(
    obj_filename: str,
    png_filename: str,
    scale: Vec3,
    translation: Vec3,
    rotation: Vec3,
) -> None:
    """Load one mesh entity (geometry + texture + transform) into the scene.

    Mirrors the C ``load_mesh``: fills the next slot of the static mesh array
    and bumps the mesh count.
    """
    if len(meshes) >= MAX_NUM_MESHES:
        return
    mesh = mesh_t()
    load_mesh_obj_data(mesh, obj_filename)
    load_mesh_png_data(mesh, png_filename)

    mesh.scale = scale
    mesh.translation = translation
    mesh.rotation = rotation

    meshes.append(mesh)


def load_mesh_obj_data(mesh: mesh_t, obj_filename: str) -> None:
    """Parse an OBJ file into the mesh's vertex and face lists.

    Supports the same subset as the C parser: ``v``, ``vt``, and triangulated
    ``f v/vt/vn`` faces. Falls back to the built-in cube when the file is
    missing (CONVENTIONS.md §8).
    """
    path = _resolve_asset_path(obj_filename)
    if not os.path.isfile(path):
        print(f"Warning: '{obj_filename}' not found - falling back to the built-in cube mesh.")
        # Prefer the generated assets/cube.obj so the OBJ parser is still
        # genuinely exercised (CONVENTIONS.md §8); only if even that file is
        # gone, use the hard-coded vertex/face tables.
        fallback_obj = os.path.join(_BASE_DIR, "assets", "cube.obj")
        if os.path.isfile(fallback_obj):
            path = fallback_obj
        else:
            _load_cube_mesh_data(mesh)
            return

    texcoords: list[tex2_t] = []

    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            # Vertex information
            if line.startswith("v "):
                parts = line.split()
                mesh.vertices.append(
                    vec3_new(float(parts[1]), float(parts[2]), float(parts[3]))
                )
            # Texture coordinate information
            if line.startswith("vt "):
                parts = line.split()
                texcoords.append(tex2_t(u=float(parts[1]), v=float(parts[2])))
            # Face information
            if line.startswith("f "):
                vertex_indices = []
                texture_indices = []
                for corner in line.split()[1:4]:
                    v_index, vt_index, _vn_index = corner.split("/")
                    vertex_indices.append(int(v_index))
                    texture_indices.append(int(vt_index))
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

    _finalize_mesh_vertices(mesh)


def load_mesh_png_data(mesh: mesh_t, png_filename: str) -> None:
    """Load the mesh's PNG texture (C: upng_new_from_file + upng_decode).

    Falls back to assets/cube.png when the file is missing (CONVENTIONS.md §8);
    like the C code, the texture is left unset if nothing can be decoded.
    """
    path = _resolve_asset_path(png_filename)
    if not os.path.isfile(path):
        print(f"Warning: '{png_filename}' not found - falling back to assets/cube.png.")
        path = os.path.join(_BASE_DIR, "assets", "cube.png")

    png_image = load_png_texture(path)
    if png_image is not None:
        mesh.texture = png_image


def _load_cube_mesh_data(mesh: mesh_t) -> None:
    """Fill the mesh with the hard-coded cube (the earlier steps' load_cube_mesh_data)."""
    for x, y, z in _CUBE_VERTICES:
        mesh.vertices.append(vec3_new(x, y, z))
    for a, b, c, a_uv, b_uv, c_uv, color in _CUBE_FACES:
        mesh.faces.append(
            face_t(
                a=a,
                b=b,
                c=c,
                a_uv=tex2_t(*a_uv),
                b_uv=tex2_t(*b_uv),
                c_uv=tex2_t(*c_uv),
                color=color,
            )
        )
    _finalize_mesh_vertices(mesh)


def _finalize_mesh_vertices(mesh: mesh_t) -> None:
    """Stack the vertex list into one (N, 4) homogeneous array (w = 1).

    Built once at load time so main.py can transform every vertex of the mesh
    with a single matmul per frame (CONVENTIONS.md §5).
    """
    if mesh.vertices:
        vertices = np.array(mesh.vertices, dtype=np.float64)
        mesh.homogeneous_vertices = np.hstack(
            [vertices, np.ones((len(mesh.vertices), 1), dtype=np.float64)]
        )


def get_num_meshes() -> int:
    """Return how many meshes were loaded into the scene."""
    return len(meshes)


def get_mesh(index: int) -> mesh_t:
    """Return the mesh at the given index of the scene's mesh array."""
    return meshes[index]


def free_meshes() -> None:
    """Release all mesh data (C: upng_free + array_free per mesh; Python: GC)."""
    meshes.clear()
