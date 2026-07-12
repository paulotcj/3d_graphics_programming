"""main.py — mirrors src/main.c (step 57: multiple meshes).

The game loop: process_input -> update -> render, at 60 FPS. NEW in this
step, ``update`` loops over **all meshes in the scene** (see mesh.py); each
mesh carries its own scale/rotation/translation and its own texture, and
setup() loads two airplanes (f22 and efa) side by side. The camera got a
pitch angle to go with its yaw, both driven from the keyboard, and every
subsystem is now accessed through getter/setter functions instead of global
structs — mirrored here 1:1.

Per-frame pipeline for every mesh face:
1. transform to world space (scale -> rotate -> translate), then to camera
   space with the look-at view matrix;
2. backface-cull against the camera origin;
3. clip the triangle against the six frustum planes (clipping.py);
4. project each resulting triangle, perspective-divide, and map to screen;
5. flat-shade from the face normal and the global light;
6. rasterize in render() according to the current render mode.

Performance improvement (CONVENTIONS.md §5): instead of C's three
mat4_mul_vec4 calls per face, ALL vertices of a mesh are transformed to
camera space with one (N, 4) @ (4, 4) matrix multiplication per frame, and
each face then gathers its three transformed vertices by index.
"""

from __future__ import annotations

import math
import os
import sys

import numpy as np
import pygame

import display
from camera import (
    get_camera_direction,
    get_camera_lookat_target,
    get_camera_position,
    get_camera_forward_velocity,
    rotate_camera_pitch,
    rotate_camera_yaw,
    update_camera_forward_velocity,
    update_camera_position,
)
from clipping import (
    clip_polygon,
    init_frustum_planes,
    polygon_from_triangle,
    triangles_from_polygon,
)
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
    clear_z_buffer,
    destroy_window,
    draw_grid,
    draw_rect,
    get_window_height,
    get_window_width,
    init_window,
    render_color_buffer,
    set_cull_method,
    set_render_method,
    should_cull_backface,
    should_render_filled_triangle,
    should_render_textured_triangle,
    should_render_wire,
    should_render_wire_vertex,
)
from light import apply_light_intensity, get_light_direction, init_light
from matrix import (
    mat4_look_at,
    mat4_make_perspective,
    mat4_make_rotation_x,
    mat4_make_rotation_y,
    mat4_make_rotation_z,
    mat4_make_scale,
    mat4_make_translation,
    mat4_mul_mat4,
    mat4_mul_vec4,
)
from mesh import free_meshes, get_mesh, get_num_meshes, load_mesh
from triangle import draw_filled_triangle, draw_textured_triangle, draw_triangle, triangle_t
from vector import (
    vec3_add,
    vec3_cross,
    vec3_dot,
    vec3_from_vec4,
    vec3_mul,
    vec3_new,
    vec3_normalize,
    vec3_sub,
)

###############################################################################
# Global variables for execution status and game loop
###############################################################################
is_running: bool = False
delta_time: float = 0.0
clock: pygame.time.Clock | None = None

###############################################################################
# Array to store triangles that should be rendered each frame
###############################################################################
MAX_TRIANGLES: int = 10000
triangles_to_render: list[triangle_t] = []

###############################################################################
# Declaration of our global transformation matrices
###############################################################################
world_matrix: np.ndarray | None = None
proj_matrix: np.ndarray | None = None
view_matrix: np.ndarray | None = None

# Test hooks (CONVENTIONS.md §7) — identical block in every step:
#   RENDERER_MAX_FRAMES=<n>      exit cleanly after n frames
#   RENDERER_SAVE_FRAME=<path>   save the final presented frame to a PNG
_max_frames_env = os.environ.get("RENDERER_MAX_FRAMES")
MAX_FRAMES: int | None = int(_max_frames_env) if _max_frames_env else None
SAVE_FRAME_PATH: str | None = os.environ.get("RENDERER_SAVE_FRAME")
frame_count: int = 0


###############################################################################
# Setup function to initialize variables and game objects
###############################################################################
def setup() -> None:
    global proj_matrix

    # Initialize render mode and triangle culling method
    set_render_method(RENDER_WIRE)
    set_cull_method(CULL_BACKFACE)

    # Initialize the scene light direction
    init_light(vec3_new(0, 0, 1))

    # Initialize the perspective projection matrix
    aspect_y = get_window_height() / get_window_width()
    aspect_x = get_window_width() / get_window_height()
    fov_y = 3.141592 / 3.0  # the same as 180/3, or 60deg
    fov_x = math.atan(math.tan(fov_y / 2) * aspect_x) * 2
    znear = 1.0
    zfar = 20.0
    proj_matrix = mat4_make_perspective(fov_y, aspect_y, znear, zfar)

    # Initialize frustum planes with a point and a normal
    init_frustum_planes(fov_x, fov_y, znear, zfar)

    load_mesh("./assets/f22.obj", "./assets/f22.png", vec3_new(1, 1, 1), vec3_new(-3, 0, +8), vec3_new(0, 0, 0))
    load_mesh("./assets/efa.obj", "./assets/efa.png", vec3_new(1, 1, 1), vec3_new(+3, 0, +8), vec3_new(0, 0, 0))


###############################################################################
# Poll system events and handle keyboard input
###############################################################################
def process_input() -> None:
    global is_running

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            is_running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                is_running = False
            elif event.key == pygame.K_1:
                set_render_method(RENDER_WIRE_VERTEX)
            elif event.key == pygame.K_2:
                set_render_method(RENDER_WIRE)
            elif event.key == pygame.K_3:
                set_render_method(RENDER_FILL_TRIANGLE)
            elif event.key == pygame.K_4:
                set_render_method(RENDER_FILL_TRIANGLE_WIRE)
            elif event.key == pygame.K_5:
                set_render_method(RENDER_TEXTURED)
            elif event.key == pygame.K_6:
                set_render_method(RENDER_TEXTURED_WIRE)
            elif event.key == pygame.K_c:
                set_cull_method(CULL_BACKFACE)
            elif event.key == pygame.K_x:
                set_cull_method(CULL_NONE)
            elif event.key == pygame.K_w:
                rotate_camera_pitch(+3.0 * delta_time)
            elif event.key == pygame.K_s:
                rotate_camera_pitch(-3.0 * delta_time)
            elif event.key == pygame.K_RIGHT:
                rotate_camera_yaw(+1.0 * delta_time)
            elif event.key == pygame.K_LEFT:
                rotate_camera_yaw(-1.0 * delta_time)
            elif event.key == pygame.K_UP:
                update_camera_forward_velocity(vec3_mul(get_camera_direction(), 5.0 * delta_time))
                update_camera_position(vec3_add(get_camera_position(), get_camera_forward_velocity()))
            elif event.key == pygame.K_DOWN:
                update_camera_forward_velocity(vec3_mul(get_camera_direction(), 5.0 * delta_time))
                update_camera_position(vec3_sub(get_camera_position(), get_camera_forward_velocity()))


###############################################################################
# Update function frame by frame with a fixed time step
###############################################################################
def update() -> None:
    global delta_time, view_matrix, world_matrix

    # Wait until we reach the target frame time (C: SDL_Delay), then get a
    # delta time factor in seconds. The clamp avoids physics jumps after a
    # stall (documented improvement, CONVENTIONS.md §7).
    assert clock is not None
    delta_time = clock.tick(FPS) / 1000.0
    if delta_time > 0.05:
        delta_time = 0.05

    # Initialize the array of triangles to render for the current frame
    triangles_to_render.clear()

    # Loop all the meshes of our scene
    for mesh_index in range(get_num_meshes()):
        mesh = get_mesh(mesh_index)

        # Create scale, rotation, and translation matrices that will be used to multiply the mesh vertices
        scale_matrix = mat4_make_scale(mesh.scale[0], mesh.scale[1], mesh.scale[2])
        translation_matrix = mat4_make_translation(
            mesh.translation[0], mesh.translation[1], mesh.translation[2]
        )
        rotation_matrix_x = mat4_make_rotation_x(mesh.rotation[0])
        rotation_matrix_y = mat4_make_rotation_y(mesh.rotation[1])
        rotation_matrix_z = mat4_make_rotation_z(mesh.rotation[2])

        # Update camera look at target to create view matrix
        target = get_camera_lookat_target()
        up_direction = vec3_new(0, 1, 0)
        view_matrix = mat4_look_at(get_camera_position(), target, up_direction)

        # Create a World Matrix combining scale, rotation, and translation matrices.
        # Order matters: First scale, then rotate, then translate. [T]*[R]*[S]*v
        world_matrix = mat4_mul_mat4(rotation_matrix_z, scale_matrix)
        world_matrix = mat4_mul_mat4(rotation_matrix_y, world_matrix)
        world_matrix = mat4_mul_mat4(rotation_matrix_x, world_matrix)
        world_matrix = mat4_mul_mat4(translation_matrix, world_matrix)

        # Transform ALL mesh vertices to camera space with one matmul
        # (replaces the C per-face-per-vertex mat4_mul_vec4 loop —
        # CONVENTIONS.md §5). Row i holds the transformed vertex i.
        camera_space_matrix = mat4_mul_mat4(view_matrix, world_matrix)
        transformed_all = mesh.homogeneous_vertices @ camera_space_matrix.T

        # Loop all triangle faces of our mesh
        for mesh_face in mesh.faces:
            # Gather the three transformed vertices of this face (1-based indices)
            transformed_vertices = transformed_all[
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
            origin = vec3_new(0, 0, 0)
            camera_ray = vec3_sub(origin, vector_a)

            # Calculate how aligned the camera ray is with the face normal (using dot product)
            dot_normal_camera = vec3_dot(normal, camera_ray)

            # Backface culling test to see if the current face should be projected
            if should_cull_backface():
                # Backface culling, bypassing triangles that are looking away from the camera
                if dot_normal_camera < 0:
                    continue

            # Create a polygon from the original transformed triangle to be clipped
            polygon = polygon_from_triangle(
                vec3_from_vec4(transformed_vertices[0]),
                vec3_from_vec4(transformed_vertices[1]),
                vec3_from_vec4(transformed_vertices[2]),
                mesh_face.a_uv,
                mesh_face.b_uv,
                mesh_face.c_uv,
            )

            # Clip the polygon and return a new polygon with potential new vertices
            clip_polygon(polygon)

            # Break the clipped polygon apart back into individual triangles
            triangles_after_clipping = triangles_from_polygon(polygon)

            # Loop all the assembled triangles after clipping
            for triangle_after_clipping in triangles_after_clipping:
                projected_points = []

                # Loop all three vertices to perform projection and conversion to screen space
                for j in range(3):
                    # Project the current vertex using a perspective projection matrix
                    projected_point = mat4_mul_vec4(
                        proj_matrix, triangle_after_clipping.points[j]
                    )

                    # Perform perspective divide
                    if projected_point[3] != 0:
                        projected_point[0] /= projected_point[3]
                        projected_point[1] /= projected_point[3]
                        projected_point[2] /= projected_point[3]

                    # Flip vertically since the y values of the 3D mesh grow bottom->up
                    # and in screen space y values grow top->down
                    projected_point[1] *= -1

                    # Scale into the view
                    projected_point[0] *= get_window_width() / 2.0
                    projected_point[1] *= get_window_height() / 2.0

                    # Translate the projected points to the middle of the screen
                    projected_point[0] += get_window_width() / 2.0
                    projected_point[1] += get_window_height() / 2.0

                    projected_points.append(projected_point)

                # Calculate the shade intensity based on how aligned is the normal
                # with the flipped light direction ray
                light_intensity_factor = -vec3_dot(normal, get_light_direction())

                # Calculate the triangle color based on the light angle
                triangle_color = apply_light_intensity(mesh_face.color, light_intensity_factor)

                # Create the final projected triangle that will be rendered in screen space
                triangle_to_render = triangle_t(
                    points=np.array(projected_points, dtype=np.float64),
                    texcoords=[
                        triangle_after_clipping.texcoords[0],
                        triangle_after_clipping.texcoords[1],
                        triangle_after_clipping.texcoords[2],
                    ],
                    color=triangle_color,
                    texture=mesh.texture,
                )

                # Save the projected triangle in the array of triangles to render
                if len(triangles_to_render) < MAX_TRIANGLES:
                    triangles_to_render.append(triangle_to_render)


###############################################################################
# Render function to draw objects on the display
###############################################################################
def render() -> None:
    global frame_count, is_running

    # Clear all the arrays to get ready for the next frame
    clear_color_buffer(0xFF000000)
    clear_z_buffer()

    draw_grid()

    # Loop all projected triangles and render them
    for triangle in triangles_to_render:
        # Draw filled triangle
        if should_render_filled_triangle():
            draw_filled_triangle(
                triangle.points[0][0], triangle.points[0][1], triangle.points[0][2], triangle.points[0][3],  # vertex A
                triangle.points[1][0], triangle.points[1][1], triangle.points[1][2], triangle.points[1][3],  # vertex B
                triangle.points[2][0], triangle.points[2][1], triangle.points[2][2], triangle.points[2][3],  # vertex C
                triangle.color,
            )

        # Draw textured triangle
        if should_render_textured_triangle():
            draw_textured_triangle(
                triangle.points[0][0], triangle.points[0][1], triangle.points[0][2], triangle.points[0][3], triangle.texcoords[0].u, triangle.texcoords[0].v,  # vertex A
                triangle.points[1][0], triangle.points[1][1], triangle.points[1][2], triangle.points[1][3], triangle.texcoords[1].u, triangle.texcoords[1].v,  # vertex B
                triangle.points[2][0], triangle.points[2][1], triangle.points[2][2], triangle.points[2][3], triangle.texcoords[2].u, triangle.texcoords[2].v,  # vertex C
                triangle.texture,
            )

        # Draw triangle wireframe
        if should_render_wire():
            draw_triangle(
                triangle.points[0][0], triangle.points[0][1],  # vertex A
                triangle.points[1][0], triangle.points[1][1],  # vertex B
                triangle.points[2][0], triangle.points[2][1],  # vertex C
                0xFFFFFFFF,
            )

        # Draw triangle vertex points
        if should_render_wire_vertex():
            draw_rect(int(triangle.points[0][0]) - 3, int(triangle.points[0][1]) - 3, 6, 6, 0xFF0000FF)  # vertex A
            draw_rect(int(triangle.points[1][0]) - 3, int(triangle.points[1][1]) - 3, 6, 6, 0xFF0000FF)  # vertex B
            draw_rect(int(triangle.points[2][0]) - 3, int(triangle.points[2][1]) - 3, 6, 6, 0xFF0000FF)  # vertex C

    # Finally draw the color buffer to the window
    render_color_buffer()

    # Test hooks (CONVENTIONS.md §7): frame counting and final-frame saving.
    frame_count += 1
    if MAX_FRAMES is not None and frame_count >= MAX_FRAMES:
        is_running = False
    if not is_running and SAVE_FRAME_PATH and display.window is not None:
        pygame.image.save(display.window, SAVE_FRAME_PATH)


###############################################################################
# Free the memory that was dynamically allocated by the program
###############################################################################
def free_resources() -> None:
    free_meshes()
    destroy_window()


###############################################################################
# Main function
###############################################################################
def main() -> None:
    global is_running, clock

    fullscreen = "--fullscreen" in sys.argv
    is_running = init_window(fullscreen)
    clock = pygame.time.Clock()

    setup()

    while is_running:
        process_input()
        update()
        render()

    free_resources()


if __name__ == "__main__":
    main()
