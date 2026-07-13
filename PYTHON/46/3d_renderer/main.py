"""main.py — mirrors src/main.c: the game loop and the 3D graphics pipeline.

Step 46 introduces the CAMERA and the LOOK-AT VIEW MATRIX. A new global
`camera` (camera.py) drifts up-right every frame while `mat4_look_at` builds
a view matrix that keeps it aimed at a hardcoded target (0, 0, 4) — the
mesh's position. Every frame, each face travels the pipeline:

    model space -> world matrix -> VIEW MATRIX (camera space) -> backface
    culling -> perspective projection -> screen space -> flat-shaded /
    textured rasterization with a z-buffer.

Because vertices are now in camera space before culling, the backface test
compares the face normal against a ray toward the origin (the camera is the
origin of camera space) instead of the old `camera_position` global.

Performance (CONVENTIONS.md §5): where the C code rebuilds the world matrix
and multiplies it vertex by vertex for every face, this version combines the
matrices once per frame and transforms ALL mesh vertices with a single NumPy
matmul, then gathers the three vertices of each face from the result.

Controls: ESC quit; 1-6 render modes; c backface culling on, d off.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pygame

import hud

import display
from display import (
    FPS,
    clear_color_buffer,
    clear_z_buffer,
    destroy_window,
    draw_grid,
    draw_rect,
    initialize_window,
    render_color_buffer,
)
from light import light, light_apply_intensity
from camera import camera
from matrix import (
    Mat4,
    mat4_identity,
    mat4_look_at,
    mat4_make_perspective,
    mat4_make_rotation_x,
    mat4_make_rotation_y,
    mat4_make_rotation_z,
    mat4_make_scale,
    mat4_make_translation,
    mat4_mul_mat4,
    mat4_mul_vec4_project,
)
import mesh as mesh_module
import texture
from mesh import load_obj_file_data, mesh
from texture import load_png_texture_data, tex2_t
from triangle import draw_filled_triangle, draw_textured_triangle, draw_triangle, triangle_t
from vector import vec3_cross, vec3_dot, vec3_from_vec4, vec3_normalize, vec3_sub


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
# Asset paths are resolved against this file, not the working directory
# (CONVENTIONS.md §7), so `python main.py` works from anywhere.
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

###############################################################################
# Global variables for execution status and game loop
###############################################################################
is_running: bool = False
clock: pygame.time.Clock | None = None  # replaces previous_frame_time + SDL_Delay

###############################################################################
# Array to store triangles that should be rendered each frame
###############################################################################
MAX_TRIANGLES: int = 10000
triangles_to_render: list[triangle_t] = []

###############################################################################
# Declaration of our global transformation matrices
###############################################################################
world_matrix: Mat4 | None = None
proj_matrix: Mat4 | None = None
view_matrix: Mat4 | None = None


###############################################################################
# Setup function to initialize variables and game objects
###############################################################################
def setup() -> None:
    """Initialize render modes, the projection matrix, and load mesh + texture."""
    global proj_matrix, clock

    clock = pygame.time.Clock()

    # Initialize render mode and triangle culling method
    display.render_method = display.RENDER_TEXTURED
    display.cull_method = display.CULL_BACKFACE

    # (The color buffer and the z-buffer are allocated in initialize_window —
    # in the C code the two mallocs live here in setup.)

    # Initialize the perspective projection matrix
    fov = 3.141592 / 3.0  # the same as 180/3, or 60deg (C uses this literal)
    aspect = display.window_height / display.window_width
    znear = 0.1
    zfar = 100.0
    proj_matrix = mat4_make_perspective(fov, aspect, znear, zfar)

    # Loads the vertex and face values for the mesh data structure
    # (missing .obj files fall back to the built-in cube, CONVENTIONS.md §8)
    load_obj_file_data(os.path.join(ASSETS_DIR, "efa.obj"))

    # Load the texture information from an external PNG file
    load_png_texture_data(os.path.join(ASSETS_DIR, "efa.png"))


###############################################################################
# Poll system events and handle keyboard input
###############################################################################
def process_input() -> None:
    """Handle window close and the step's keyboard controls.

    Mirrors main.c: 1-6 select the render method, c/d toggle backface culling
    on/off. (The C code polls a single event per frame; polling the whole
    queue here fixes that input lag — CONVENTIONS.md §10.)
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
            if event.key == pygame.K_5:
                display.render_method = display.RENDER_TEXTURED
            if event.key == pygame.K_6:
                display.render_method = display.RENDER_TEXTURED_WIRE
            if event.key == pygame.K_c:
                display.cull_method = display.CULL_BACKFACE
            if event.key == pygame.K_d:
                display.cull_method = display.CULL_NONE


###############################################################################
# Update function frame by frame with a fixed time step
###############################################################################
def update() -> None:
    """Animate the mesh and camera, transform, cull, light, and project every face."""
    global world_matrix, view_matrix

    # Wait some time until we reach the target frame time (C: SDL_Delay).
    assert clock is not None
    clock.tick(FPS)

    # Initialize the counter of triangles to render for the current frame
    triangles_to_render.clear()

    # Change the mesh scale, rotation, and translation values per animation frame
    mesh.rotation[0] += 0.006
    mesh.rotation[1] += 0.000
    mesh.rotation[2] += 0.000
    mesh.translation[2] = 4.0

    # Change the camera position per animation frame
    camera.position[0] += 0.008
    camera.position[1] += 0.008
    # Create the view matrix looking at a hardcoded target point
    target = np.array([0.0, 0.0, 4.0])
    up_direction = np.array([0.0, 1.0, 0.0])
    view_matrix = mat4_look_at(camera.position, target, up_direction)
    # Create scale, rotation, and translation matrices that will be used to multiply the mesh vertices
    scale_matrix = mat4_make_scale(mesh.scale[0], mesh.scale[1], mesh.scale[2])
    translation_matrix = mat4_make_translation(mesh.translation[0], mesh.translation[1], mesh.translation[2])
    rotation_matrix_x = mat4_make_rotation_x(mesh.rotation[0])
    rotation_matrix_y = mat4_make_rotation_y(mesh.rotation[1])
    rotation_matrix_z = mat4_make_rotation_z(mesh.rotation[2])

    # Create a World Matrix combining scale, rotation, and translation matrices.
    # Order matters (right-to-left on column vectors): first scale, then
    # rotate z, y, x, then translate — the C code's [T]*[R]*[S]*v.
    world_matrix = mat4_identity()
    world_matrix = mat4_mul_mat4(scale_matrix, world_matrix)
    world_matrix = mat4_mul_mat4(rotation_matrix_z, world_matrix)
    world_matrix = mat4_mul_mat4(rotation_matrix_y, world_matrix)
    world_matrix = mat4_mul_mat4(rotation_matrix_x, world_matrix)
    world_matrix = mat4_mul_mat4(translation_matrix, world_matrix)

    # Batch-transform ALL mesh vertices to world space and then to camera
    # space in one matmul each (CONVENTIONS.md §5) instead of C's
    # per-face-per-vertex mat4_mul_vec4. Row-vector trick: (M @ v) for every
    # column vector v == V @ M.T where V stacks the vertices as rows.
    world_space_vertices = mesh_module.mesh_homogeneous_vertices @ world_matrix.T
    # Multiply the view matrix by every vector to transform the scene to camera space
    camera_space_vertices = world_space_vertices @ view_matrix.T

    # Loop all triangle faces of our mesh
    for mesh_face in mesh.faces:
        # Gather the three transformed vertices of this face (1-based indices)
        transformed_vertices = camera_space_vertices[
            [mesh_face.a - 1, mesh_face.b - 1, mesh_face.c - 1]
        ]

        # Get individual vectors from A, B, and C vertices to compute normal
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
        # (vertices are in camera space now, so the camera sits at the origin)
        origin = np.array([0.0, 0.0, 0.0])
        camera_ray = vec3_sub(origin, vector_a)

        # Calculate how aligned the camera ray is with the face normal (using dot product)
        dot_normal_camera = vec3_dot(normal, camera_ray)

        # Backface culling test to see if the current face should be projected
        if display.cull_method == display.CULL_BACKFACE:
            # Backface culling, bypassing triangles that are looking away from the camera
            if dot_normal_camera < 0:
                continue

        projected_points = []

        # Loop all three vertices to perform projection and conversion to screen space
        for j in range(3):
            # Project the current vertex
            projected_point = mat4_mul_vec4_project(proj_matrix, transformed_vertices[j])

            # Flip vertically since the y values of the 3D mesh grow bottom->up
            # and in screen space y values grow top->down
            projected_point[1] *= -1

            # Scale into the view
            projected_point[0] *= display.window_width / 2.0
            projected_point[1] *= display.window_height / 2.0

            # Translate the projected points to the middle of the screen
            projected_point[0] += display.window_width / 2.0
            projected_point[1] += display.window_height / 2.0

            projected_points.append(projected_point)

        # Calculate the shade intensity based on how aligned is the normal
        # with the flipped light direction ray
        light_intensity_factor = -vec3_dot(normal, light.direction)

        # Calculate the triangle color based on the light angle
        triangle_color = light_apply_intensity(mesh_face.color, light_intensity_factor)

        # Create the final projected triangle that will be rendered in screen space
        projected_triangle = triangle_t(
            points=np.array(projected_points, dtype=np.float64),
            texcoords=[
                tex2_t(mesh_face.a_uv.u, mesh_face.a_uv.v),
                tex2_t(mesh_face.b_uv.u, mesh_face.b_uv.v),
                tex2_t(mesh_face.c_uv.u, mesh_face.c_uv.v),
            ],
            color=triangle_color,
        )

        # Save the projected triangle in the array of triangles to render
        if len(triangles_to_render) < MAX_TRIANGLES:
            triangles_to_render.append(projected_triangle)


###############################################################################
# Render function to draw objects on the display
###############################################################################
def render() -> None:
    """Rasterize this frame's triangles, present, then clear for the next frame."""
    draw_grid()

    # Loop all projected triangles and render them
    for triangle in triangles_to_render:
        # Draw filled triangle
        if display.render_method in (display.RENDER_FILL_TRIANGLE, display.RENDER_FILL_TRIANGLE_WIRE):
            draw_filled_triangle(
                triangle.points[0][0], triangle.points[0][1], triangle.points[0][2], triangle.points[0][3],  # vertex A
                triangle.points[1][0], triangle.points[1][1], triangle.points[1][2], triangle.points[1][3],  # vertex B
                triangle.points[2][0], triangle.points[2][1], triangle.points[2][2], triangle.points[2][3],  # vertex C
                triangle.color,
            )

        # Draw textured triangle
        if display.render_method in (display.RENDER_TEXTURED, display.RENDER_TEXTURED_WIRE):
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
            display.RENDER_WIRE,
            display.RENDER_WIRE_VERTEX,
            display.RENDER_FILL_TRIANGLE_WIRE,
            display.RENDER_TEXTURED_WIRE,
        ):
            draw_triangle(
                int(triangle.points[0][0]), int(triangle.points[0][1]),  # vertex A
                int(triangle.points[1][0]), int(triangle.points[1][1]),  # vertex B
                int(triangle.points[2][0]), int(triangle.points[2][1]),  # vertex C
                0xFFFFFFFF,
            )

        # Draw triangle vertex points
        if display.render_method == display.RENDER_WIRE_VERTEX:
            draw_rect(int(triangle.points[0][0]) - 3, int(triangle.points[0][1]) - 3, 6, 6, 0xFF0000FF)  # vertex A
            draw_rect(int(triangle.points[1][0]) - 3, int(triangle.points[1][1]) - 3, 6, 6, 0xFF0000FF)  # vertex B
            draw_rect(int(triangle.points[2][0]) - 3, int(triangle.points[2][1]) - 3, 6, 6, 0xFF0000FF)  # vertex C

    # Finally draw the color buffer to the SDL window
    render_color_buffer()

    # Clear all the arrays to get ready for the next frame
    clear_color_buffer(0xFF000000)
    clear_z_buffer()


###############################################################################
# Free the memory that was dynamically allocated by the program
###############################################################################
def free_resources() -> None:
    """Release the mesh data (C: free + upng_free + array_free; Python: GC)."""
    mesh.faces.clear()
    mesh.vertices.clear()


###############################################################################
# Main function
###############################################################################
def main() -> None:
    """Entry point: init, setup, then the process-update-render loop."""
    global is_running

    is_running = initialize_window(fullscreen="--fullscreen" in sys.argv)

    setup()

    # --- Test hooks (CONVENTIONS.md §7, identical in every step) -------------
    max_frames = int(os.environ.get("RENDERER_MAX_FRAMES", "0"))  # 0 = unlimited
    save_frame_path = os.environ.get("RENDERER_SAVE_FRAME", "")
    frames_rendered = 0
    # -------------------------------------------------------------------------

    while is_running:
        process_input()
        update()
        render()

        # --- Test hooks: exit cleanly after RENDERER_MAX_FRAMES frames ------
        frames_rendered += 1
        if max_frames and frames_rendered >= max_frames:
            is_running = False
        # ---------------------------------------------------------------------

    # --- Test hooks: save the final presented frame to a PNG ----------------
    if save_frame_path and display.window is not None:
        pygame.image.save(display.window, save_frame_path)
    # -------------------------------------------------------------------------

    destroy_window()
    free_resources()


if __name__ == "__main__":
    main()
