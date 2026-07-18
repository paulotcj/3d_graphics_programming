"""main.py — mirrors src/main.c (step 53: triangles from the clipped polygon).

The game loop: process_input -> update -> render, at 60 FPS. NEW in this
step, the clipped polygon is finally broken back into triangles with
``triangles_from_polygon`` (fan triangulation: n vertices -> n - 2
triangles), and it is those *clipped* triangles that get projected and
drawn. The previous step's debug line that skipped every face but index 4
is removed — the whole cube is back — and the mesh rotates again
(0.1/0.2/0.3 rad/s around x/y/z) at z = 5.

Per-frame pipeline per face:
1. transform to world space (scale -> rotate -> translate), then to camera
   space with the look-at view matrix;
2. backface-cull against the camera origin;
3. build a polygon from the triangle and clip it against all six frustum
   planes (Sutherland-Hodgman);
4. break the clipped polygon back into triangles (NEW);
5. project each resulting triangle, perspective-divide, and map to screen;
6. flat-shade from the face normal and the global light;
7. rasterize in render() according to the current render mode.

Performance improvement (CONVENTIONS.md §5): instead of C's three
mat4_mul_vec4 calls per face, ALL vertices of the mesh are transformed to
camera space with one (N, 4) @ (4, 4) matrix multiplication per frame, and
each face then gathers its three transformed vertices by index.
"""

from __future__ import annotations

import math
import os
import sys

import numpy as np
import pygame

import hud

import display
import texture
from camera import camera
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
    initialize_window,
    render_color_buffer,
)
from light import light, light_apply_intensity
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
from mesh import load_obj_file_data, mesh
from texture import load_png_texture_data
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
    ("5", "textured"),
    ("6", "textured + wireframe"),
    ("C", "backface culling ON"),
    ("X", "backface culling OFF"),
    ("Up", "move camera up"),
    ("Down", "move camera down"),
    ("A", "turn camera left"),
    ("D", "turn camera right"),
]
hud.init_hud(KEY_BINDINGS)
# Asset paths are resolved against this file, not the working directory
# (CONVENTIONS.md §7), so `python main.py` works from anywhere.
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

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

# All mesh vertices stacked as homogeneous rows (N, 4) for the batched
# per-frame transform (CONVENTIONS.md §5) — built once in setup().
mesh_homogeneous_vertices: np.ndarray | None = None

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
    global proj_matrix, mesh_homogeneous_vertices

    # Initialize render mode and triangle culling method
    display.render_method = RENDER_WIRE
    display.cull_method = CULL_BACKFACE

    # Allocate the required memory to hold the color buffer and the z-buffer
    # (C: malloc in setup; here NumPy arrays, CONVENTIONS.md §2/§4)
    display.color_buffer = np.zeros(
        (display.window_height, display.window_width), dtype=np.uint32
    )
    display.z_buffer = np.ones(
        (display.window_height, display.window_width), dtype=np.float32
    )

    # Initialize the perspective projection matrix.
    # NEW in step 53: the vertical fov (fov_y) is the classic 60 degrees, and
    # the horizontal fov (fov_x) is derived from it through the aspect ratio
    # — atan(tan(fov_y/2) * aspect_x) * 2 — so the left/right frustum planes
    # can finally match the screen's real proportions.
    aspect_y = display.window_height / display.window_width
    aspect_x = display.window_width / display.window_height
    fov_y = 3.141592 / 3.0  # the same as 180/3, or 60deg
    fov_x = math.atan(math.tan(fov_y / 2) * aspect_x) * 2
    z_near = 1.0
    z_far = 20.0
    proj_matrix = mat4_make_perspective(fov_y, aspect_y, z_near, z_far)

    # Initialize frustum planes with a point and a normal
    init_frustum_planes(fov_x, fov_y, z_near, z_far)

    # Loads the vertex and face values for the mesh data structure
    load_obj_file_data(os.path.join(ASSETS_DIR, "cube.obj"))

    # Load the texture information from an external PNG file
    load_png_texture_data(os.path.join(ASSETS_DIR, "cube.png"))

    # Stack all mesh vertices as homogeneous rows once — the per-frame
    # transform is then a single matmul (CONVENTIONS.md §5).
    vertex_rows = np.array(mesh.vertices, dtype=np.float64)
    mesh_homogeneous_vertices = np.hstack(
        [vertex_rows, np.ones((len(mesh.vertices), 1), dtype=np.float64)]
    )


###############################################################################
# Poll system events and handle keyboard input
###############################################################################
def process_input() -> None:
    """Handle window close and this step's keyboard controls.

    Improvement noted per CONVENTIONS.md §10: the C code polls a single event
    per frame (`SDL_PollEvent` once); here the whole queue is drained each
    frame, which removes the input lag without changing any behavior.
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
            if event.key == pygame.K_x:
                display.cull_method = CULL_NONE

    # Continuous camera movement: held keys act every frame (scaled by
    # delta_time), matching the C's reliance on SDL key-repeat. Discrete
    # toggles above stay one-shot on KEYDOWN.
    keys = pygame.key.get_pressed()
    if keys[pygame.K_UP]:
        camera.position[1] += 3.0 * delta_time
    if keys[pygame.K_DOWN]:
        camera.position[1] -= 3.0 * delta_time
    if keys[pygame.K_a]:
        camera.yaw -= 1.0 * delta_time
    if keys[pygame.K_d]:
        camera.yaw += 1.0 * delta_time
    if keys[pygame.K_w]:
        camera.forward_velocity = vec3_mul(camera.direction, 5.0 * delta_time)
        camera.position = vec3_add(camera.position, camera.forward_velocity)
    if keys[pygame.K_s]:
        camera.forward_velocity = vec3_mul(camera.direction, 5.0 * delta_time)
        camera.position = vec3_sub(camera.position, camera.forward_velocity)


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

    # Change the mesh scale, rotation, and translation values per animation frame
    mesh.rotation[0] += 0.1 * delta_time
    mesh.rotation[1] += 0.2 * delta_time
    mesh.rotation[2] += 0.3 * delta_time
    mesh.translation[2] = 5.0

    # Initialize the target looking at the positive z-axis
    target = vec3_new(0, 0, 1)
    camera_yaw_rotation = mat4_make_rotation_y(camera.yaw)
    camera.direction = vec3_from_vec4(mat4_mul_vec4(camera_yaw_rotation, vec4_from_vec3(target)))

    # Offset the camera position in the direction where the camera is pointing at
    target = vec3_add(camera.position, camera.direction)
    up_direction = vec3_new(0, 1, 0)

    # Create the view matrix
    view_matrix = mat4_look_at(camera.position, target, up_direction)

    # Create scale, rotation, and translation matrices that will be used to multiply the mesh vertices
    scale_matrix = mat4_make_scale(mesh.scale[0], mesh.scale[1], mesh.scale[2])
    translation_matrix = mat4_make_translation(
        mesh.translation[0], mesh.translation[1], mesh.translation[2]
    )
    rotation_matrix_x = mat4_make_rotation_x(mesh.rotation[0])
    rotation_matrix_y = mat4_make_rotation_y(mesh.rotation[1])
    rotation_matrix_z = mat4_make_rotation_z(mesh.rotation[2])

    # Create a World Matrix combining scale, rotation, and translation matrices.
    # Order matters: First scale, then rotate, then translate. [T]*[R]*[S]*v
    world_matrix = mat4_mul_mat4(rotation_matrix_z, scale_matrix)
    world_matrix = mat4_mul_mat4(rotation_matrix_y, world_matrix)
    world_matrix = mat4_mul_mat4(rotation_matrix_x, world_matrix)
    world_matrix = mat4_mul_mat4(translation_matrix, world_matrix)

    # Transform ALL mesh vertices to camera space with one matmul
    # (replaces the C per-face-per-vertex mat4_mul_vec4 loop —
    # CONVENTIONS.md §5). Row i holds the transformed vertex i.
    assert mesh_homogeneous_vertices is not None
    camera_space_matrix = mat4_mul_mat4(view_matrix, world_matrix)
    transformed_all = mesh_homogeneous_vertices @ camera_space_matrix.T

    # Loop all triangle faces of our mesh
    num_faces = len(mesh.faces)
    for i in range(num_faces):
        mesh_face = mesh.faces[i]

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
        if display.cull_method == CULL_BACKFACE:
            # Backface culling, bypassing triangles that are looking away from the camera
            if dot_normal_camera < 0:
                continue

        # Create a polygon from the original transformed triangle to be clipped
        polygon = polygon_from_triangle(
            vec3_from_vec4(transformed_vertices[0]),
            vec3_from_vec4(transformed_vertices[1]),
            vec3_from_vec4(transformed_vertices[2]),
        )

        # Clip the polygon and returns a new polygon with potential new vertices
        clip_polygon(polygon)

        # Break the clipped polygon apart back into individual triangles
        # (C fills a triangle_t[] plus an out-parameter count; the Python
        # helper returns the list directly)
        triangles_after_clipping = triangles_from_polygon(polygon)

        # Loops all the assembled triangles after clipping
        for triangle_after_clipping in triangles_after_clipping:
            projected_points = []

            # Loop all three vertices to perform projection and conversion to screen space
            for j in range(3):
                # Project the current vertex using a perspective projection matrix
                projected_point = mat4_mul_vec4(proj_matrix, triangle_after_clipping.points[j])

                # Perform perspective divide
                if projected_point[3] != 0:
                    projected_point[0] /= projected_point[3]
                    projected_point[1] /= projected_point[3]
                    projected_point[2] /= projected_point[3]

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
            triangle_to_render = triangle_t(
                points=np.array(projected_points, dtype=np.float64),
                texcoords=[
                    mesh_face.a_uv,
                    mesh_face.b_uv,
                    mesh_face.c_uv,
                ],
                color=triangle_color,
            )

            # Save the projected triangle in the array of triangles to render
            if len(triangles_to_render) < MAX_TRIANGLES:
                triangles_to_render.append(triangle_to_render)


###############################################################################
# Render function to draw objects on the display
###############################################################################
def render() -> None:
    global frame_count, is_running

    # Clear all the arrays to get ready for the next frame. (The C code clears
    # them at the END of render, after presenting — same visible result.)
    clear_color_buffer(0xFF000000)
    clear_z_buffer()

    draw_grid()

    # Loop all projected triangles and render them
    for triangle in triangles_to_render:
        # Draw filled triangle
        if display.render_method in (RENDER_FILL_TRIANGLE, RENDER_FILL_TRIANGLE_WIRE):
            draw_filled_triangle(
                triangle.points[0][0], triangle.points[0][1], triangle.points[0][2], triangle.points[0][3],  # vertex A
                triangle.points[1][0], triangle.points[1][1], triangle.points[1][2], triangle.points[1][3],  # vertex B
                triangle.points[2][0], triangle.points[2][1], triangle.points[2][2], triangle.points[2][3],  # vertex C
                triangle.color,
            )

        # Draw textured triangle
        if display.render_method in (RENDER_TEXTURED, RENDER_TEXTURED_WIRE):
            draw_textured_triangle(
                triangle.points[0][0], triangle.points[0][1], triangle.points[0][2], triangle.points[0][3], triangle.texcoords[0].u, triangle.texcoords[0].v,  # vertex A
                triangle.points[1][0], triangle.points[1][1], triangle.points[1][2], triangle.points[1][3], triangle.texcoords[1].u, triangle.texcoords[1].v,  # vertex B
                triangle.points[2][0], triangle.points[2][1], triangle.points[2][2], triangle.points[2][3], triangle.texcoords[2].u, triangle.texcoords[2].v,  # vertex C
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
    # C frees the buffers, the PNG, and the mesh arrays here; Python's garbage
    # collector owns that memory, so only the window must be shut down.
    destroy_window()


###############################################################################
# Main function
###############################################################################
def main() -> None:
    global is_running, clock

    fullscreen = "--fullscreen" in sys.argv
    is_running = initialize_window(fullscreen)
    clock = pygame.time.Clock()

    setup()

    while is_running:
        process_input()
        update()
        render()

    free_resources()


if __name__ == "__main__":
    main()
