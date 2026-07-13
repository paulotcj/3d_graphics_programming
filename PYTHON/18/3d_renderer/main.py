"""Step 18 — triangle meshes: vertices and faces (mirrors src/main.c).

The point cloud is gone. Geometry is now a **mesh**: 8 cube vertices plus 12
faces that index into them (see mesh.py). Each frame, ``update()`` walks the
faces, gathers each face's three vertices, rotates and translates them,
projects them, and stores the result as a ``triangle_t``; ``render()`` then
marks the three projected corners of every triangle with small yellow
squares. The wireframe lines connecting them arrive in step 19.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pygame

import hud

import display
from mesh import N_MESH_FACES, mesh_faces, mesh_vertices
from triangle import triangle_t
from vector import Vec2, Vec3, vec3_rotate_x, vec3_rotate_y, vec3_rotate_z


# Key bindings shown by the on-screen help (press H). Derived from the
# actual handlers in process_input below.
KEY_BINDINGS: list[tuple[str, str]] = [
    ("ESC", "quit"),
]
hud.init_hud(KEY_BINDINGS)
###############################################################################
# Array of triangles that should be rendered frame by frame
###############################################################################
triangles_to_render: list[triangle_t] = [triangle_t() for _ in range(N_MESH_FACES)]

camera_position: Vec3 = np.array([0.0, 0.0, -5.0], dtype=np.float64)
cube_rotation: Vec3 = np.array([0.0, 0.0, 0.0], dtype=np.float64)

fov_factor: float = 640.0

is_running: bool = False

clock: pygame.time.Clock | None = None


def setup() -> None:
    """Nothing left to build here — the mesh is hard-coded in mesh.py.

    (The C setup() only allocates the color buffer and texture, which
    display.initialize_window() already did; the step-17 point-cloud loop is
    deleted.)
    """


def process_input() -> None:
    """Handle window close and the ESC key.

    The C code polls a single event per frame (SDL_PollEvent once); draining
    the whole queue avoids the classic input-lag bug (CONVENTIONS.md §10).
    """
    global is_running

    for event in pygame.event.get():
        hud.handle_event(event)  # H toggles the key-bindings help
        if event.type == pygame.QUIT:
            is_running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                is_running = False


def project(point: Vec3) -> Vec2:
    """Receive a 3D vector and return a perspective-projected 2D point.

    Remember: similar triangles — (smaller side)/(larger side) ==
    (smaller base)/(larger base), therefore X' == X/Z, scaled by fov_factor.
    """
    return np.array(
        [
            (fov_factor * point[0]) / point[2],
            (fov_factor * point[1]) / point[2],
        ],
        dtype=np.float64,
    )


def update() -> None:
    """Cap the frame rate, then transform and project every mesh face.

    Mirrors update() in main.c: for each of the 12 faces, look up its three
    vertices (1-based indexes!), rotate each around x/y/z, push it away from
    the camera, project it, and center it on screen. The projected triangle
    lands in triangles_to_render for render() to draw.
    """
    assert clock is not None
    clock.tick(display.FPS)  # C: SDL_Delay pacing to FRAME_TARGET_TIME

    cube_rotation[0] += 0.01
    cube_rotation[1] += 0.01
    cube_rotation[2] += 0.01

    # Loop all triangle faces of our mesh
    for i in range(N_MESH_FACES):
        mesh_face = mesh_faces[i]

        face_vertices = (
            mesh_vertices[mesh_face.a - 1],  # C and .obj indexes are 1-based
            mesh_vertices[mesh_face.b - 1],
            mesh_vertices[mesh_face.c - 1],
        )

        projected_triangle = triangle_t()

        # Loop all three vertices of this current face and apply transformations
        for j in range(3):
            transformed_vertex = vec3_rotate_x(face_vertices[j], cube_rotation[0])
            transformed_vertex = vec3_rotate_y(transformed_vertex, cube_rotation[1])
            transformed_vertex = vec3_rotate_z(transformed_vertex, cube_rotation[2])

            # Translate the vertex away from the camera
            transformed_vertex[2] -= camera_position[2]

            # Project the current vertex
            projected_point = project(transformed_vertex)

            # Scale and translate the projected points to the middle of the screen
            projected_point[0] += display.window_width / 2
            projected_point[1] += display.window_height / 2

            projected_triangle.points[j] = projected_point

        # Save the projected triangle in the array of triangles to render
        triangles_to_render[i] = projected_triangle


def render() -> None:
    """Draw the grid and a 3x3 marker on every projected vertex, then present."""
    display.draw_grid()

    # Loop all projected triangles and render their vertex positions
    for i in range(N_MESH_FACES):
        triangle = triangles_to_render[i]
        display.draw_rect(int(triangle.points[0][0]), int(triangle.points[0][1]), 3, 3, 0xFFFFFF00)
        display.draw_rect(int(triangle.points[1][0]), int(triangle.points[1][1]), 3, 3, 0xFFFFFF00)
        display.draw_rect(int(triangle.points[2][0]), int(triangle.points[2][1]), 3, 3, 0xFFFFFF00)

    display.render_color_buffer()

    display.clear_color_buffer(0xFF000000)


def main() -> None:
    """Mirrors main() in main.c: initialize, then loop input/update/render."""
    global is_running, clock

    is_running = display.initialize_window(fullscreen="--fullscreen" in sys.argv)

    setup()

    # Test hooks (CONVENTIONS.md §7) — identical block in every step:
    # RENDERER_MAX_FRAMES=<n> exits cleanly after n frames;
    # RENDERER_SAVE_FRAME=<path.png> saves the last presented frame on exit.
    max_frames_env = os.environ.get("RENDERER_MAX_FRAMES")
    max_frames = int(max_frames_env) if max_frames_env else None
    save_frame_path = os.environ.get("RENDERER_SAVE_FRAME")
    frames_rendered = 0

    clock = pygame.time.Clock()

    while is_running:
        process_input()
        update()
        render()

        frames_rendered += 1
        if max_frames is not None and frames_rendered >= max_frames:
            is_running = False

    if save_frame_path and display.window is not None:
        pygame.image.save(display.window, save_frame_path)

    display.destroy_window()


if __name__ == "__main__":
    main()
