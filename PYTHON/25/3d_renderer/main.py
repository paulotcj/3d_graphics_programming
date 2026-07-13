"""Step 25 — backface culling (mirrors src/main.c).

Triangles facing away from the camera are now skipped before projection.
For each face: build the two edge vectors AB and AC, take their **cross
product** to get the face normal (the winding order in mesh.py makes it
point outward), then **dot** the normal with the ray from the face to the
camera. A negative dot product means the face looks away — cull it. The
wireframe stops being see-through: only the front of the cube is drawn.

The camera also moves to the origin (the mesh is pushed +5 into the screen
instead), and the vertex marker rects are dropped from render().

Pipeline per frame (same as the C code):
    process_input -> update (rotate + project) -> render (grid + triangles)
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pygame

import hud

import display
import mesh
from display import (
    FPS,
    clear_color_buffer,
    destroy_window,
    draw_grid,
    draw_rect,
    draw_triangle,
    initialize_window,
    render_color_buffer,
)
from triangle import triangle_t
from vector import (
    Vec2,
    Vec3,
    vec2_new,
    vec3_cross,
    vec3_dot,
    vec3_new,
    vec3_rotate_x,
    vec3_rotate_y,
    vec3_rotate_z,
    vec3_sub,
)


# Key bindings shown by the on-screen help (press H). Derived from the
# actual handlers in process_input below.
KEY_BINDINGS: list[tuple[str, str]] = [
    ("ESC", "quit"),
]
hud.init_hud(KEY_BINDINGS)
###############################################################################
# Array of triangles that should be rendered frame by frame
###############################################################################
triangles_to_render: list[triangle_t] = []

###############################################################################
# Global variables for execution status and game loop
###############################################################################
is_running: bool = False

camera_position: Vec3 = vec3_new(0, 0, 0)  # step 25: the camera sits at the origin
fov_factor: float = 640

# pygame Clock replaces the C SDL_Delay/FRAME_TARGET_TIME bookkeeping —
# clock.tick(FPS) waits exactly like the C "time_to_wait" block did.
clock: pygame.time.Clock | None = None


def setup() -> None:
    """Allocate the color buffer and load the mesh from disk (C: setup())."""
    # Allocate the required memory to hold the color buffer. (The C code also
    # creates an SDL streaming texture here; pygame builds the equivalent
    # surface on the fly in display.render_color_buffer().)
    display.color_buffer = np.zeros(
        (display.window_height, display.window_width), dtype=np.uint32
    )

    # Loads the vertex and face values for the mesh data structure
    # mesh.load_cube_mesh_data()
    # C: load_obj_file_data("./assets/f22.obj") — the path is resolved
    # against this file so it works from any working directory (§7).
    mesh.load_obj_file_data(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "cube.obj"))


def process_input() -> None:
    """Poll events and handle the keyboard (C: process_input()).

    Improvement over this step's C code (CONVENTIONS.md §10): the C version
    polls a single event per frame, which lags when events queue up; here we
    drain the whole queue every frame, as the C code itself does in later
    steps.
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

    Similar triangles: the projected x is scaled by 1/z, so points twice as
    far away appear half as big. fov_factor scales the result to pixels.
    """
    projected_point = vec2_new(
        (fov_factor * point[0]) / point[2],
        (fov_factor * point[1]) / point[2],
    )
    return projected_point


def update() -> None:
    """Rotate the mesh and build the list of projected triangles (C: update()).

    Mirrors the C loop 1:1: for each face, rotate its three vertices with the
    per-axis helpers, push them away from the camera, and perspective-project
    them to screen space. The cube is tiny (12 faces x 3 vertices = 36
    rotations per frame), so this stays scalar for side-by-side readability
    with the C; only per-pixel work is vectorized (CONVENTIONS.md §5).
    """
    global triangles_to_render

    # Initialize the array of triangles to render (C: triangles_to_render = NULL)
    triangles_to_render = []

    mesh.mesh.rotation[0] += 0.01
    mesh.mesh.rotation[1] += 0.01
    mesh.mesh.rotation[2] += 0.02

    # Loop all triangle faces of our mesh
    num_faces = len(mesh.mesh.faces)
    for i in range(num_faces):
        mesh_face = mesh.mesh.faces[i]

        face_vertices = [
            mesh.mesh.vertices[mesh_face.a - 1],
            mesh.mesh.vertices[mesh_face.b - 1],
            mesh.mesh.vertices[mesh_face.c - 1],
        ]

        transformed_vertices: list[Vec3] = []

        # Loop all three vertices of this current face and apply transformations
        for j in range(3):
            transformed_vertex = face_vertices[j]

            transformed_vertex = vec3_rotate_x(transformed_vertex, mesh.mesh.rotation[0])
            transformed_vertex = vec3_rotate_y(transformed_vertex, mesh.mesh.rotation[1])
            transformed_vertex = vec3_rotate_z(transformed_vertex, mesh.mesh.rotation[2])

            # Translate the vertices away from the camera
            transformed_vertex[2] += 5

            # Save transformed vertex in the array of transformed vertices
            transformed_vertices.append(transformed_vertex)

        # Check backface culling
        vector_a = transformed_vertices[0]  # .   A
        vector_b = transformed_vertices[1]  # .  / .
        vector_c = transformed_vertices[2]  # . C---B

        # Get the vector subtraction of B-A and C-A
        vector_ab = vec3_sub(vector_b, vector_a)
        vector_ac = vec3_sub(vector_c, vector_a)

        # Compute the face normal (using cross product to find perpendicular)
        normal = vec3_cross(vector_ab, vector_ac)

        # Find the vector between a point in the triangle and the camera origin
        camera_ray = vec3_sub(camera_position, vector_a)

        # Calculate how aligned the camera ray is with the face normal (using dot product)
        dot_normal_camera = vec3_dot(normal, camera_ray)

        # Bypass the triangles that are looking away from the camera
        if dot_normal_camera < 0:
            continue

        projected_triangle = triangle_t()

        # Loop all three vertices to perform projection
        for j in range(3):
            # Project the current vertex
            projected_point = project(transformed_vertices[j])

            # Scale and translate the projected points to the middle of the screen
            projected_point[0] += display.window_width / 2
            projected_point[1] += display.window_height / 2

            projected_triangle.points[j] = projected_point

        # Save the projected triangle in the array of triangles to render
        triangles_to_render.append(projected_triangle)


def render() -> None:
    """Draw the grid and every projected triangle, then present (C: render())."""
    draw_grid()

    # Loop all projected triangles and render them
    for triangle in triangles_to_render:
        # Draw unfilled triangle
        draw_triangle(
            int(triangle.points[0][0]), int(triangle.points[0][1]),  # vertex A
            int(triangle.points[1][0]), int(triangle.points[1][1]),  # vertex B
            int(triangle.points[2][0]), int(triangle.points[2][1]),  # vertex C
            0xFF00FF00,
        )

    # (C frees the triangles array here; the Python list is rebuilt in update.)

    render_color_buffer()

    clear_color_buffer(0xFF000000)


def free_resources() -> None:
    """Release the dynamically allocated data (C: free_resources()).

    Python's garbage collector does the real freeing; this mirrors the C
    call structure so the shutdown sequence reads the same.
    """
    display.color_buffer = None
    mesh.mesh.faces.clear()
    mesh.mesh.vertices.clear()


def main() -> None:
    """Entry point — same structure as the C main()."""
    global is_running, clock

    is_running = initialize_window(fullscreen="--fullscreen" in sys.argv)

    setup()

    # --- Test hooks (identical in every step — CONVENTIONS.md §7) ------------
    max_frames_env = os.environ.get("RENDERER_MAX_FRAMES")
    max_frames = int(max_frames_env) if max_frames_env else None
    save_frame_path = os.environ.get("RENDERER_SAVE_FRAME")
    frame_count = 0
    # -------------------------------------------------------------------------

    clock = pygame.time.Clock()

    while is_running:
        clock.tick(FPS)  # C: SDL_Delay until FRAME_TARGET_TIME has elapsed

        process_input()
        update()
        render()

        # --- Test hooks ------------------------------------------------------
        frame_count += 1
        if max_frames is not None and frame_count >= max_frames:
            is_running = False
        # -----------------------------------------------------------------------

    # Save the last presented frame if requested (test hook).
    if save_frame_path and display.window is not None:
        pygame.image.save(display.window, save_frame_path)

    destroy_window()
    free_resources()


if __name__ == "__main__":
    main()
