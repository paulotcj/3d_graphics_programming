"""Step 30 — 4x4 matrices and the scale transform (mirrors src/main.c).

The renderer switches from per-axis trigonometry helpers to **matrices**.
matrix.py introduces mat4_t with the identity, a scale matrix, and
matrix-times-vector; vertices are promoted to 4 components (vec4, w = 1) so
one matrix can eventually carry every transform. In this step ONLY the scale
matrix is applied — the rotation angles keep accumulating but are not used —
and mesh.scale grows a little every frame, so the cube visibly inflates
(x faster than y). Rotation and translation matrices arrive next.
"""

from __future__ import annotations

import os
import sys

import pygame

import hud

import display
from matrix import mat4_make_scale, mat4_mul_vec4
import mesh
from triangle import draw_filled_triangle, draw_triangle, triangle_t
from vector import (
    Vec2,
    Vec3,
    Vec4,
    vec2_new,
    vec3_cross,
    vec3_dot,
    vec3_from_vec4,
    vec3_new,
    vec3_normalize,
    vec3_sub,
    vec4_from_vec3,
)


# Key bindings shown by the on-screen help (press H). Derived from the
# actual handlers in process_input below.
KEY_BINDINGS: list[tuple[str, str]] = [
    ("ESC", "quit"),
    ("1", "wireframe + vertex markers"),
    ("2", "wireframe"),
    ("3", "filled triangles"),
    ("4", "filled + wireframe"),
    ("C", "backface culling ON"),
    ("D", "backface culling OFF"),
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

    # Initialize render mode and triangle culling method
    display.render_method = display.RENDER_WIRE
    display.cull_method = display.CULL_BACKFACE

    # Allocate the required memory to hold the color buffer
    # (the SDL streaming texture has no pygame equivalent — the buffer is
    # presented directly in display.render_color_buffer()).
    display.create_color_buffer()

    clock = pygame.time.Clock()

    # Loads the vertex and face values for the mesh data structure
    mesh.load_cube_mesh_data()
    # asset_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "cube.obj")
    # mesh.load_obj_file_data(asset_path)


###############################################################################
# Poll system events and handle keyboard input
###############################################################################
def process_input() -> None:
    """Handle quit, ESC, render-mode keys (1-4) and culling keys (c/d).

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
            if event.key == pygame.K_1:
                display.render_method = display.RENDER_WIRE_VERTEX
            if event.key == pygame.K_2:
                display.render_method = display.RENDER_WIRE
            if event.key == pygame.K_3:
                display.render_method = display.RENDER_FILL_TRIANGLE
            if event.key == pygame.K_4:
                display.render_method = display.RENDER_FILL_TRIANGLE_WIRE
            if event.key == pygame.K_c:
                display.cull_method = display.CULL_BACKFACE
            if event.key == pygame.K_d:
                display.cull_method = display.CULL_NONE


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

    # Change the mesh scale/rotation values per animation frame
    mesh.mesh.rotation[0] += 0.01
    mesh.mesh.rotation[1] += 0.01
    mesh.mesh.rotation[2] += 0.01
    mesh.mesh.scale[0] += 0.002
    mesh.mesh.scale[1] += 0.001

    # Create a scale matrix that will be used to multiply the mesh vertices
    scale_matrix = mat4_make_scale(mesh.mesh.scale[0], mesh.mesh.scale[1], mesh.mesh.scale[2])

    # Loop all triangle faces of our mesh
    for mesh_face in mesh.mesh.faces:
        face_vertices = [
            mesh.mesh.vertices[mesh_face.a - 1],
            mesh.mesh.vertices[mesh_face.b - 1],
            mesh.mesh.vertices[mesh_face.c - 1],
        ]

        transformed_vertices: list[Vec4] = []

        # Loop all three vertices of this current face and apply transformations
        for face_vertex in face_vertices:
            transformed_vertex = vec4_from_vec3(face_vertex)

            # Use a matrix to scale our original vertex
            transformed_vertex = mat4_mul_vec4(scale_matrix, transformed_vertex)

            # Translate the vertex away from the camera
            transformed_vertex[2] += 5

            # Save transformed vertex in the array of transformed vertices
            transformed_vertices.append(transformed_vertex)

        # Backface culling test to see if the current face should be projected
        if display.cull_method == display.CULL_BACKFACE:
            vector_a = vec3_from_vec4(transformed_vertices[0])  # /*   A   */
            vector_b = vec3_from_vec4(transformed_vertices[1])  # /*  / \  */
            vector_c = vec3_from_vec4(transformed_vertices[2])  # /* C---B */

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

        projected_points: list[Vec2] = []

        # Loop all three vertices to perform projection
        for j in range(3):
            # Project the current vertex
            projected_point = project(vec3_from_vec4(transformed_vertices[j]))

            # Scale and translate the projected points to the middle of the screen
            projected_point[0] += display.window_width / 2
            projected_point[1] += display.window_height / 2

            projected_points.append(projected_point)

        # Calculate the average depth for each face based on the vertices after transformation
        avg_depth = (
            transformed_vertices[0][2] + transformed_vertices[1][2] + transformed_vertices[2][2]
        ) / 3.0

        projected_triangle = triangle_t(
            color=mesh_face.color,
            avg_depth=avg_depth,
        )
        projected_triangle.points[0] = projected_points[0]
        projected_triangle.points[1] = projected_points[1]
        projected_triangle.points[2] = projected_points[2]

        # Save the projected triangle in the array of triangles to render
        triangles_to_render.append(projected_triangle)

    # Sort the triangles to render by their avg_depth, back to front (painter's
    # algorithm). The C code uses a hand-rolled O(n^2) selection/bubble sort;
    # Python's built-in sort with reverse=True produces the same back-to-front
    # order (largest avg_depth first) — noted in the README as an improvement.
    triangles_to_render.sort(key=lambda triangle: triangle.avg_depth, reverse=True)


###############################################################################
# Render function to draw objects on the display
###############################################################################
def render() -> None:
    """Draw the grid and every projected triangle per render_method, then present."""
    # C calls SDL_RenderClear(renderer) here; pygame has no separate renderer
    # to clear — clear_color_buffer() at the end of this function does the job.
    display.draw_grid()

    # Loop all projected triangles and render them
    for triangle in triangles_to_render:
        # Draw filled triangle
        if display.render_method in (
            display.RENDER_FILL_TRIANGLE,
            display.RENDER_FILL_TRIANGLE_WIRE,
        ):
            draw_filled_triangle(
                triangle.points[0][0], triangle.points[0][1],  # vertex A
                triangle.points[1][0], triangle.points[1][1],  # vertex B
                triangle.points[2][0], triangle.points[2][1],  # vertex C
                triangle.color,
            )

        # Draw triangle wireframe
        if display.render_method in (
            display.RENDER_WIRE,
            display.RENDER_WIRE_VERTEX,
            display.RENDER_FILL_TRIANGLE_WIRE,
        ):
            draw_triangle(
                triangle.points[0][0], triangle.points[0][1],  # vertex A
                triangle.points[1][0], triangle.points[1][1],  # vertex B
                triangle.points[2][0], triangle.points[2][1],  # vertex C
                0xFFFFFFFF,
            )

        # Draw triangle vertex points
        if display.render_method == display.RENDER_WIRE_VERTEX:
            display.draw_rect(triangle.points[0][0] - 3, triangle.points[0][1] - 3, 6, 6, 0xFFFF0000)  # vertex A
            display.draw_rect(triangle.points[1][0] - 3, triangle.points[1][1] - 3, 6, 6, 0xFFFF0000)  # vertex B
            display.draw_rect(triangle.points[2][0] - 3, triangle.points[2][1] - 3, 6, 6, 0xFFFF0000)  # vertex C

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
