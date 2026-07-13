"""main.py — mirrors src/main.c.

Game loop for step 39 of the 3D renderer: **perspective-correct texture
mapping**. Projected vertices now keep their full (x, y, z, w) — the
original camera-space depth survives in ``w`` — and the textured rasterizer
interpolates u/w, v/w, and 1/w instead of plain u and v, so the red-brick
texture no longer warps as the cube rotates (the affine distortion visible
in step 38 is gone). The cube spins slowly around y only, making the
correction easy to see on the large front face.

Pipeline per frame: process_input -> update (transform + cull + light +
project + painter's-algorithm sort) -> render (rasterize the triangle list).
"""

from __future__ import annotations

import math
import os
import sys

import numpy as np
import pygame

import hud

import display
import mesh
import texture
from display import (
    CULL_BACKFACE,
    CULL_NONE,
    FPS,
    RENDER_FILL_TRIANGLE,
    RENDER_FILL_TRIANGLE_WIRE,
    RENDER_TEXTURED,
    RENDER_TEXTURED_WIRE,
    RENDER_WIRE,
    RENDER_WIRE_VERTEX,
    clear_color_buffer,
    destroy_window,
    draw_grid,
    draw_rect,
    initialize_window,
    render_color_buffer,
)
from light import light, light_apply_intensity
from matrix import (
    Mat4,
    mat4_identity,
    mat4_make_perspective,
    mat4_make_rotation_x,
    mat4_make_rotation_y,
    mat4_make_rotation_z,
    mat4_make_scale,
    mat4_make_translation,
    mat4_mul_mat4,
    mat4_mul_vec4_project,
)
from texture import REDBRICK_TEXTURE, tex2_t
from triangle import (
    draw_filled_triangle,
    draw_textured_triangle,
    draw_triangle,
    triangle_t,
)
from vector import Vec3, vec3_new


# Key bindings shown by the on-screen help (press H). Derived from the
# actual handlers in process_input below.
KEY_BINDINGS: list[tuple[str, str]] = [
    ("ESC", "quit"),
    ("1", "wireframe + vertex markers"),
    ("2", "wireframe"),
    ("3", "filled triangles"),
    ("4", "filled + wireframe"),
    ("5", "textured"),
    ("6", "textured + wireframe"),
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
clock: pygame.time.Clock | None = None

camera_position: Vec3 = vec3_new(0, 0, 0)
proj_matrix: Mat4 = mat4_identity()

# --- Test hooks (CONVENTIONS.md §7) — identical block in every step. -------
# RENDERER_MAX_FRAMES=<n>       exit cleanly after n frames.
# RENDERER_SAVE_FRAME=<path>    save the final presented frame to a PNG.
MAX_FRAMES: int = int(os.environ.get("RENDERER_MAX_FRAMES", "0"))
SAVE_FRAME_PATH: str = os.environ.get("RENDERER_SAVE_FRAME", "")
frame_count: int = 0
# ---------------------------------------------------------------------------


###############################################################################
# Setup function to initialize variables and game objects
###############################################################################
def setup() -> None:
    """Initialize modes, projection matrix, texture, and mesh (C: also mallocs)."""
    global proj_matrix

    # Initialize render mode and triangle culling method
    display.render_method = RENDER_TEXTURED_WIRE
    display.cull_method = CULL_BACKFACE

    # (The color buffer is allocated in initialize_window — display.py owns
    # all display state in the Python conversion.)

    # Initialize the perspective projection matrix
    fov = math.pi / 3.0  # the same as 180/3, or 60deg
    aspect = display.window_height / display.window_width
    znear = 0.1
    zfar = 100.0
    proj_matrix = mat4_make_perspective(fov, aspect, znear, zfar)

    # Manually load the hardcoded texture data from the static array
    texture.mesh_texture = REDBRICK_TEXTURE
    texture.texture_width = 64
    texture.texture_height = 64

    # Loads the vertex and face values for the mesh data structure
    mesh.load_cube_mesh_data()
    # mesh.load_obj_file_data(os.path.join(os.path.dirname(__file__), "assets", "f22.obj"))


###############################################################################
# Poll system events and handle keyboard input
###############################################################################
def process_input() -> None:
    """Handle quit, ESC, render-mode keys 1-6, and cull toggles c / d.

    The C code polls a single SDL event per frame; we drain the whole queue
    (an allowed input-lag fix, CONVENTIONS.md §10).
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
                display.render_method = RENDER_WIRE_VERTEX
            if event.key == pygame.K_2:
                display.render_method = RENDER_WIRE
            if event.key == pygame.K_3:
                display.render_method = RENDER_FILL_TRIANGLE
            if event.key == pygame.K_4:
                display.render_method = RENDER_FILL_TRIANGLE_WIRE
            if event.key == pygame.K_5:
                display.render_method = RENDER_TEXTURED
            if event.key == pygame.K_6:
                display.render_method = RENDER_TEXTURED_WIRE
            if event.key == pygame.K_c:
                display.cull_method = CULL_BACKFACE
            if event.key == pygame.K_d:
                display.cull_method = CULL_NONE


###############################################################################
# Update function frame by frame with a fixed time step
###############################################################################
def update() -> None:
    """Transform, cull, light, project, and depth-sort all faces this frame."""
    global triangles_to_render

    # Wait some time until we reach the target frame time
    # (C: SDL_Delay math; pygame's Clock does the same wait.)
    assert clock is not None
    clock.tick(FPS)

    # Initialize the array of triangles to render
    triangles_to_render = []

    # Change the mesh scale, rotation, and translation values per animation frame
    mesh.mesh.rotation[0] += 0.000
    mesh.mesh.rotation[1] += 0.003
    mesh.mesh.rotation[2] += 0.000
    mesh.mesh.translation[2] = 5.0

    # Create scale, rotation, and translation matrices that will be used to multiply the mesh vertices
    scale_matrix = mat4_make_scale(*mesh.mesh.scale)
    translation_matrix = mat4_make_translation(*mesh.mesh.translation)
    rotation_matrix_x = mat4_make_rotation_x(mesh.mesh.rotation[0])
    rotation_matrix_y = mat4_make_rotation_y(mesh.mesh.rotation[1])
    rotation_matrix_z = mat4_make_rotation_z(mesh.mesh.rotation[2])

    # Create a World Matrix combining scale, rotation, and translation matrices.
    # Order matters: First scale, then rotate, then translate. [T]*[R]*[S]*v
    # (C rebuilds this identical matrix once per vertex; hoisting it out of
    # the loop is a documented improvement — the product is the same.)
    world_matrix = mat4_identity()
    world_matrix = mat4_mul_mat4(scale_matrix, world_matrix)
    world_matrix = mat4_mul_mat4(rotation_matrix_z, world_matrix)
    world_matrix = mat4_mul_mat4(rotation_matrix_y, world_matrix)
    world_matrix = mat4_mul_mat4(rotation_matrix_x, world_matrix)
    world_matrix = mat4_mul_mat4(translation_matrix, world_matrix)

    # Transform ALL mesh vertices with one matmul (CONVENTIONS.md §5) instead
    # of C's per-face-per-vertex mat4_mul_vec4 calls. Rows are vertices, so
    # right-multiplying by world_matrix.T applies the matrix to each row.
    vertices = np.asarray(mesh.mesh.vertices, dtype=np.float64)  # (N, 3)
    homogeneous = np.hstack(
        [vertices, np.ones((len(vertices), 1), dtype=np.float64)]
    )  # (N, 4) — vec4_from_vec3 for every vertex at once
    transformed = homogeneous @ world_matrix.T  # (N, 4)

    # Loop all triangle faces of our mesh
    for mesh_face in mesh.mesh.faces:
        # Gather the three transformed vertices of this face (1-based indices)
        transformed_vertices = transformed[
            [mesh_face.a - 1, mesh_face.b - 1, mesh_face.c - 1]
        ]

        # Get individual vectors from A, B, and C vertices to compute normal
        vector_a = transformed_vertices[0][:3]  # /*   A   */
        vector_b = transformed_vertices[1][:3]  # /*  / \  */
        vector_c = transformed_vertices[2][:3]  # /* C---B */

        # Get the vector subtraction of B-A and C-A, normalized like the C code
        vector_ab = vector_b - vector_a
        vector_ac = vector_c - vector_a
        vector_ab = vector_ab / np.linalg.norm(vector_ab)  # vec3_normalize
        vector_ac = vector_ac / np.linalg.norm(vector_ac)  # vec3_normalize

        # Compute the face normal (using cross product to find perpendicular)
        normal = np.cross(vector_ab, vector_ac)  # vec3_cross
        normal = normal / np.linalg.norm(normal)  # vec3_normalize

        # Find the vector between vertex A in the triangle and the camera origin
        camera_ray = camera_position - vector_a

        # Calculate how aligned the camera ray is with the face normal (using dot product)
        dot_normal_camera = float(np.dot(normal, camera_ray))  # vec3_dot

        # Backface culling test to see if the current face should be projected
        if display.cull_method == CULL_BACKFACE:
            # Backface culling, bypassing triangles that are looking away from the camera
            if dot_normal_camera < 0:
                continue

        projected_points = []

        # Loop all three vertices to perform projection
        for j in range(3):
            # Project the current vertex
            projected_point = mat4_mul_vec4_project(proj_matrix, transformed_vertices[j])

            # Flip vertically since the y values of the 3D mesh grow bottom->up and in screen space y values grow top->down
            projected_point[1] *= -1

            # Scale into the view
            projected_point[0] *= display.window_width / 2.0
            projected_point[1] *= display.window_height / 2.0

            # Translate the projected points to the middle of the screen
            projected_point[0] += display.window_width / 2.0
            projected_point[1] += display.window_height / 2.0

            projected_points.append(projected_point)

        # Calculate the average depth for each face based on the vertices after transformation
        avg_depth = float(
            transformed_vertices[0][2]
            + transformed_vertices[1][2]
            + transformed_vertices[2][2]
        ) / 3.0

        # Calculate the shade intensity based on how aligned is the normal with the flipped light direction ray
        light_intensity_factor = -float(np.dot(normal, light.direction))  # -vec3_dot

        # Calculate the triangle color based on the light angle
        triangle_color = light_apply_intensity(mesh_face.color, light_intensity_factor)

        projected_triangle = triangle_t(
            points=np.array(projected_points, dtype=np.float64),  # 3 x (x, y, z, w)
            texcoords=[
                tex2_t(mesh_face.a_uv.u, mesh_face.a_uv.v),
                tex2_t(mesh_face.b_uv.u, mesh_face.b_uv.v),
                tex2_t(mesh_face.c_uv.u, mesh_face.c_uv.v),
            ],
            color=triangle_color,
            avg_depth=avg_depth,
        )

        # Save the projected triangle in the array of triangles to render
        triangles_to_render.append(projected_triangle)

    # Sort the triangles to render by their avg_depth, farthest first
    # (painter's algorithm). C: an O(n^2) selection-style swap sort; Python's
    # built-in sort produces the same descending order in O(n log n).
    triangles_to_render.sort(key=lambda t: t.avg_depth, reverse=True)


###############################################################################
# Render function to draw objects on the display
###############################################################################
def render() -> None:
    """Rasterize this frame's triangle list into the color buffer and present it."""
    draw_grid()

    # Loop all projected triangles and render them
    for triangle in triangles_to_render:
        # Draw filled triangle
        if display.render_method in (RENDER_FILL_TRIANGLE, RENDER_FILL_TRIANGLE_WIRE):
            draw_filled_triangle(
                triangle.points[0][0], triangle.points[0][1],  # vertex A
                triangle.points[1][0], triangle.points[1][1],  # vertex B
                triangle.points[2][0], triangle.points[2][1],  # vertex C
                triangle.color,
            )

        # Draw textured triangle
        if display.render_method in (RENDER_TEXTURED, RENDER_TEXTURED_WIRE):
            draw_textured_triangle(
                triangle.points[0][0], triangle.points[0][1], triangle.points[0][2], triangle.points[0][3],
                triangle.texcoords[0].u, triangle.texcoords[0].v,  # vertex A
                triangle.points[1][0], triangle.points[1][1], triangle.points[1][2], triangle.points[1][3],
                triangle.texcoords[1].u, triangle.texcoords[1].v,  # vertex B
                triangle.points[2][0], triangle.points[2][1], triangle.points[2][2], triangle.points[2][3],
                triangle.texcoords[2].u, triangle.texcoords[2].v,  # vertex C
                texture.mesh_texture,
            )

        # Draw triangle wireframe
        if display.render_method in (
            RENDER_WIRE,
            RENDER_WIRE_VERTEX,
            RENDER_FILL_TRIANGLE_WIRE,
            RENDER_TEXTURED_WIRE,
        ):
            draw_triangle(
                triangle.points[0][0], triangle.points[0][1],  # vertex A
                triangle.points[1][0], triangle.points[1][1],  # vertex B
                triangle.points[2][0], triangle.points[2][1],  # vertex C
                0xFFFFFFFF,
            )

        # Draw triangle vertex points
        if display.render_method == RENDER_WIRE_VERTEX:
            draw_rect(int(triangle.points[0][0]) - 3, int(triangle.points[0][1]) - 3, 6, 6, 0xFFFF0000)  # vertex A
            draw_rect(int(triangle.points[1][0]) - 3, int(triangle.points[1][1]) - 3, 6, 6, 0xFFFF0000)  # vertex B
            draw_rect(int(triangle.points[2][0]) - 3, int(triangle.points[2][1]) - 3, 6, 6, 0xFFFF0000)  # vertex C

    render_color_buffer()

    clear_color_buffer(0xFF000000)


###############################################################################
# Free the memory that was dynamically allocated by the program
###############################################################################
def free_resources() -> None:
    """C parity: free the color buffer and mesh arrays (Python GC handles it)."""
    mesh.mesh.faces.clear()
    mesh.mesh.vertices.clear()


###############################################################################
# Main function
###############################################################################
def main() -> int:
    global is_running, clock, frame_count

    is_running = initialize_window(fullscreen="--fullscreen" in sys.argv)
    clock = pygame.time.Clock()

    setup()

    while is_running:
        process_input()
        update()
        render()

        # --- Test hooks (CONVENTIONS.md §7) --------------------------------
        frame_count += 1
        if MAX_FRAMES and frame_count >= MAX_FRAMES:
            is_running = False
        # -------------------------------------------------------------------

    # Save the final presented frame if requested (RENDERER_SAVE_FRAME).
    if SAVE_FRAME_PATH and display.window is not None:
        pygame.image.save(display.window, SAVE_FRAME_PATH)

    destroy_window()
    free_resources()

    return 0


if __name__ == "__main__":
    sys.exit(main())
