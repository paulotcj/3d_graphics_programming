"""main.py — mirrors src/main.c (step 27).

The game loop: process_input -> update -> render. This step renders the mesh
as SOLID WHITE filled triangles (the new flat-top/flat-bottom rasterizer in
triangle.py) with a black wireframe drawn on top, after backface culling and
the simple perspective-divide projection.

Test hooks (CONVENTIONS.md §7): RENDERER_MAX_FRAMES exits cleanly after n
frames; RENDERER_SAVE_FRAME saves the last presented frame to a PNG.
"""

from __future__ import annotations

import os
import sys

import pygame

import hud

import display
import mesh
from triangle import draw_filled_triangle, triangle_t
from vector import (
    Vec2,
    Vec3,
    vec2_new,
    vec3_cross,
    vec3_dot,
    vec3_new,
    vec3_normalize,
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

camera_position: Vec3 = vec3_new(0, 0, 0)
fov_factor: float = 640

# Frame pacing: pygame's Clock replaces the C SDL_Delay/FRAME_TARGET_TIME
# bookkeeping (previous_frame_time) — same 60 FPS cap.
clock: pygame.time.Clock | None = None

# --- Test hooks (identical in every step, CONVENTIONS.md §7) -----------------
max_frames: int = int(os.environ.get("RENDERER_MAX_FRAMES", "0"))
save_frame_path: str = os.environ.get("RENDERER_SAVE_FRAME", "")
frame_count: int = 0
# -----------------------------------------------------------------------------


###############################################################################
# Setup function to initialize variables and game objects
###############################################################################
def setup() -> None:
    """Allocate the color buffer and load the mesh (C: setup())."""
    global clock

    # Allocate the required memory to hold the color buffer
    # (the SDL streaming texture has no pygame equivalent — the buffer is
    # presented directly in display.render_color_buffer()).
    display.create_color_buffer()

    clock = pygame.time.Clock()

    # Loads the vertex and face values for the mesh data structure
    # load_cube_mesh_data()
    asset_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "cube.obj")
    mesh.load_obj_file_data(asset_path)


###############################################################################
# Poll system events and handle keyboard input
###############################################################################
def process_input() -> None:
    """Handle quit and ESC.

    Improvement over this step's C code (allowed per CONVENTIONS.md §10):
    the C version polls a single event per frame, which lags when events
    queue up; we drain the whole queue each frame.
    """
    global is_running
    for event in pygame.event.get():
        hud.handle_event(event)  # H toggles the key-bindings help
        if event.type == pygame.QUIT:
            is_running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                is_running = False


###############################################################################
# Function that receives a 3D vector and returns a projected 2D point
###############################################################################
def project(point: Vec3) -> Vec2:
    """Perspective-divide projection: scale x and y by fov_factor / z."""
    return vec2_new(
        (fov_factor * point[0]) / point[2],
        (fov_factor * point[1]) / point[2],
    )


###############################################################################
# Update function frame by frame with a fixed time step
###############################################################################
def update() -> None:
    """Rotate the mesh, transform + cull + project every face."""
    # C waits here with SDL_Delay until FRAME_TARGET_TIME has elapsed;
    # clock.tick(FPS) in main() does the same job.

    # Initialize the array of triangles to render
    triangles_to_render.clear()

    mesh.mesh.rotation[0] += 0.01
    mesh.mesh.rotation[1] += 0.01
    mesh.mesh.rotation[2] += 0.01

    # Loop all triangle faces of our mesh
    for mesh_face in mesh.mesh.faces:
        face_vertices = [
            mesh.mesh.vertices[mesh_face.a - 1],
            mesh.mesh.vertices[mesh_face.b - 1],
            mesh.mesh.vertices[mesh_face.c - 1],
        ]

        transformed_vertices: list[Vec3] = []

        # Loop all three vertices of this current face and apply transformations
        for face_vertex in face_vertices:
            transformed_vertex = vec3_rotate_x(face_vertex, mesh.mesh.rotation[0])
            transformed_vertex = vec3_rotate_y(transformed_vertex, mesh.mesh.rotation[1])
            transformed_vertex = vec3_rotate_z(transformed_vertex, mesh.mesh.rotation[2])

            # Translate the vertex away from the camera
            transformed_vertex[2] += 5

            # Save transformed vertex in the array of transformed vertices
            transformed_vertices.append(transformed_vertex)

        # Check backface culling
        vector_a = transformed_vertices[0]  # /*   A   */
        vector_b = transformed_vertices[1]  # /*  / \  */
        vector_c = transformed_vertices[2]  # /* C---B */

        # Get the vector subtraction of B-A and C-A
        vector_ab = vec3_sub(vector_b, vector_a)
        vector_ac = vec3_sub(vector_c, vector_a)
        vec3_normalize(vector_ab)
        vec3_normalize(vector_ac)

        # Compute the face normal (using cross product to find perpendicular)
        normal = vec3_cross(vector_ab, vector_ac)
        vec3_normalize(normal)

        # Find the vector between vertex A in the triangle and the camera origin
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


###############################################################################
# Render function to draw objects on the display
###############################################################################
def render() -> None:
    """Draw the grid and every projected triangle, then present the buffer."""
    display.draw_grid()

    # Loop all projected triangles and render them
    for triangle in triangles_to_render:
        # Draw filled triangle
        draw_filled_triangle(
            triangle.points[0][0], triangle.points[0][1],  # vertex A
            triangle.points[1][0], triangle.points[1][1],  # vertex B
            triangle.points[2][0], triangle.points[2][1],  # vertex C
            0xFFFFFFFF,
        )
        # Draw unfilled triangle
        display.draw_triangle(
            triangle.points[0][0], triangle.points[0][1],  # vertex A
            triangle.points[1][0], triangle.points[1][1],  # vertex B
            triangle.points[2][0], triangle.points[2][1],  # vertex C
            0xFF000000,
        )

    display.render_color_buffer()

    display.clear_color_buffer(0xFF000000)


###############################################################################
# Free the memory that was dynamically allocated by the program
###############################################################################
def free_resources() -> None:
    """C frees the color buffer and mesh arrays; Python's GC handles it."""
    mesh.mesh.vertices.clear()
    mesh.mesh.faces.clear()


###############################################################################
# Main function
###############################################################################
def main() -> None:
    global is_running, frame_count

    is_running = display.initialize_window(fullscreen="--fullscreen" in sys.argv)

    setup()

    while is_running:
        process_input()
        update()
        render()

        # --- Test hooks (CONVENTIONS.md §7) ----------------------------------
        frame_count += 1
        if max_frames and frame_count >= max_frames:
            is_running = False
        # ----------------------------------------------------------------------

        assert clock is not None
        clock.tick(display.FPS)

    if save_frame_path and display.window is not None:
        pygame.image.save(display.window, save_frame_path)

    display.destroy_window()
    free_resources()


if __name__ == "__main__":
    main()
