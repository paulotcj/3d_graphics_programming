"""main.py — mirrors src/main.c: the game loop and the 3D graphics pipeline.

This is the final step of the course: the complete software renderer. Every
frame, each mesh's triangles travel the full pipeline:

    +-------------+
    | Model space |  <-- original mesh vertices
    +-------------+
    |   +-------------+
    `-> | World space |  <-- multiply by world matrix
        +-------------+
        |   +--------------+
        `-> | Camera space |  <-- multiply by view matrix
            +--------------+
            |    +------------+
            `--> |  Clipping  |  <-- clip against the six frustum planes
                 +------------+
                 |    +------------+
                 `--> | Projection |  <-- multiply by projection matrix
                      +------------+
                      |    +-------------+
                      `--> | Image space |  <-- apply perspective divide
                           +-------------+
                           |    +--------------+
                           `--> | Screen space |  <-- ready to render
                                +--------------+

Performance (CONVENTIONS.md §5): where the C code multiplies world and view
matrices per face per vertex, this version combines them once per mesh and
transforms ALL mesh vertices with a single NumPy matmul, then gathers the
three vertices of each face from the result.

Controls: ESC quit; 1-6 render modes; c/x backface culling on/off;
w/s pitch; left/right arrows yaw; up/down arrows move forward/backward.
"""

from __future__ import annotations

import math
import os
import sys

import numpy as np
import pygame

import hud

import display
from camera import (
    get_camera_direction,
    get_camera_forward_velocity,
    get_camera_lookat_target,
    get_camera_position,
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
    Mat4,
    mat4_look_at,
    mat4_make_perspective,
    mat4_make_rotation_x,
    mat4_make_rotation_y,
    mat4_make_rotation_z,
    mat4_make_scale,
    mat4_make_translation,
    mat4_mul_vec4,
)
from mesh import free_meshes, get_mesh, get_num_meshes, load_mesh, mesh_t
from triangle import get_triangle_normal, draw_filled_triangle, draw_textured_triangle, draw_triangle, triangle_t
from vector import vec3_add, vec3_dot, vec3_from_vec4, vec3_mul, vec3_new, vec3_sub


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
    ("W", "pitch camera up"),
    ("S", "pitch camera down"),
    ("Right", "turn camera right"),
    ("Left", "turn camera left"),
    ("Up", "move camera forward"),
    ("Down", "move camera backward"),
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
world_matrix: Mat4 | None = None
proj_matrix: Mat4 | None = None
view_matrix: Mat4 | None = None


###############################################################################
# Setup function to initialize variables and game objects
###############################################################################
def setup() -> None:
    """Initialize render modes, the light, the projection matrix, the frustum
    planes, and load the four scene meshes."""
    global proj_matrix, clock

    clock = pygame.time.Clock()

    # Initialize render mode and triangle culling method
    set_render_method(RENDER_TEXTURED)
    set_cull_method(CULL_BACKFACE)

    # Initialize the scene light direction
    init_light(vec3_new(0, 0, 1))

    # Initialize the perspective projection matrix.
    # fov_y is the vertical field of view; fov_x is derived from it through
    # the aspect ratio (tan(fov_x/2) = tan(fov_y/2) * aspect_x) and is needed
    # by the left/right frustum planes.
    aspect_y = get_window_height() / get_window_width()
    aspect_x = get_window_width() / get_window_height()
    fov_y = math.pi / 3.0  # the same as 180/3, or 60deg
    fov_x = math.atan(math.tan(fov_y / 2) * aspect_x) * 2
    znear = 1.0
    zfar = 50.0
    proj_matrix = mat4_make_perspective(fov_y, aspect_y, znear, zfar)

    # Initialize frustum planes with a point and a normal
    init_frustum_planes(fov_x, fov_y, znear, zfar)

    # Loads mesh entities (missing .obj files fall back to the built-in cube,
    # CONVENTIONS.md §8 — drop the course models into assets/ to see them).
    load_mesh(os.path.join(ASSETS_DIR, "runway.obj"), os.path.join(ASSETS_DIR, "runway.png"),
              vec3_new(1, 1, 1), vec3_new(0, -1.5, +23), vec3_new(0, 0, 0))
    load_mesh(os.path.join(ASSETS_DIR, "f22.obj"), os.path.join(ASSETS_DIR, "f22.png"),
              vec3_new(1, 1, 1), vec3_new(0, -1.3, +5), vec3_new(0, -math.pi / 2, 0))
    load_mesh(os.path.join(ASSETS_DIR, "efa.obj"), os.path.join(ASSETS_DIR, "efa.png"),
              vec3_new(1, 1, 1), vec3_new(-2, -1.3, +9), vec3_new(0, -math.pi / 2, 0))
    load_mesh(os.path.join(ASSETS_DIR, "f117.obj"), os.path.join(ASSETS_DIR, "f117.png"),
              vec3_new(1, 1, 1), vec3_new(+2, -1.3, +9), vec3_new(0, -math.pi / 2, 0))


###############################################################################
# Poll system events and handle keyboard input
###############################################################################
def process_input() -> None:
    """Handle window close and the step's keyboard controls.

    Mirrors main.c exactly: 1-6 select the render method, c/x toggle backface
    culling, w/s pitch the camera, left/right arrows yaw it, and up/down
    arrows move it along its current direction. Camera speeds are scaled by
    delta_time, just like the C code.
    """
    global is_running
    for event in pygame.event.get():
        hud.handle_event(event)  # H toggles the key-bindings help
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
# Process the graphics pipeline stages for all the mesh triangles
###############################################################################
def process_graphics_pipeline_stages(mesh: mesh_t) -> None:
    """Run one mesh through the pipeline (see module docstring diagram).

    Produces screen-space triangles appended to ``triangles_to_render``.
    """
    global world_matrix, view_matrix

    # Create scale, rotation, and translation matrices that will be used to multiply the mesh vertices
    scale_matrix = mat4_make_scale(mesh.scale[0], mesh.scale[1], mesh.scale[2])
    translation_matrix = mat4_make_translation(mesh.translation[0], mesh.translation[1], mesh.translation[2])
    rotation_matrix_x = mat4_make_rotation_x(mesh.rotation[0])
    rotation_matrix_y = mat4_make_rotation_y(mesh.rotation[1])
    rotation_matrix_z = mat4_make_rotation_z(mesh.rotation[2])

    # Update camera look at target to create view matrix
    target = get_camera_lookat_target()
    up_direction = vec3_new(0, 1, 0)
    view_matrix = mat4_look_at(get_camera_position(), target, up_direction)

    # Create a World Matrix combining scale, rotation, and translation matrices.
    # Order matters (right-to-left on column vectors): first scale, then
    # rotate z, y, x, then translate — the C code's [T]*[R]*[S]*v.
    world_matrix = translation_matrix @ rotation_matrix_x @ rotation_matrix_y @ rotation_matrix_z @ scale_matrix

    # Batch-transform ALL mesh vertices to camera space in one matmul
    # (CONVENTIONS.md §5) instead of C's per-face-per-vertex mat4_mul_vec4.
    # Row-vector trick: (M @ v) for every column vector v == V @ M.T where V
    # stacks the vertices as rows.
    camera_space_vertices = mesh.homogeneous_vertices @ (view_matrix @ world_matrix).T

    # Loop all triangle faces of our mesh
    for mesh_face in mesh.faces:
        # Gather the three transformed vertices of this face (1-based indices)
        transformed_vertices = camera_space_vertices[
            [mesh_face.a - 1, mesh_face.b - 1, mesh_face.c - 1]
        ]

        # Calculate the triangle face normal
        face_normal = get_triangle_normal(transformed_vertices)

        # Backface culling test to see if the current face should be projected
        if should_cull_backface():
            # Find the vector between vertex A in the triangle and the camera origin
            camera_ray = vec3_sub(vec3_new(0, 0, 0), vec3_from_vec4(transformed_vertices[0]))

            # Calculate how aligned the camera ray is with the face normal (using dot product)
            dot_normal_camera = vec3_dot(face_normal, camera_ray)

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

        # Clip the polygon and get a new polygon with potential new vertices
        clip_polygon(polygon)

        # Break the clipped polygon apart back into a list of triangles
        triangles_after_clipping = triangles_from_polygon(polygon)

        # Loops all the assembled triangles after clipping
        for triangle_after_clipping in triangles_after_clipping:
            projected_points = []

            # Loop all three vertices to perform projection and conversion to screen space
            for v in range(3):
                # Project the current vertex using a perspective projection matrix
                projected_point = mat4_mul_vec4(proj_matrix, triangle_after_clipping.points[v])

                # Perform perspective divide: dividing x and y by the depth
                # (stored in w) is what makes far objects smaller on screen.
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
            # with the flipped light direction ray (lit faces point AGAINST
            # the incoming light, hence the negation — see light.py).
            light_intensity_factor = -vec3_dot(face_normal, get_light_direction())

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
# Update function frame by frame with a fixed time step
###############################################################################
def update() -> None:
    """Cap the frame rate, compute delta_time, and run the pipeline per mesh."""
    global delta_time

    # Wait until the target frame time is reached (C: SDL_Delay); tick()
    # returns the milliseconds elapsed since the previous frame. delta_time
    # is clamped to 0.05 s so a stall never causes a huge camera jump
    # (documented improvement, CONVENTIONS.md §7).
    assert clock is not None
    elapsed_ms = clock.tick(FPS)
    delta_time = min(elapsed_ms / 1000.0, 0.05)

    # Initialize the array of triangles to render for the current frame
    triangles_to_render.clear()

    # Loop all scene meshes
    for mesh_index in range(get_num_meshes()):
        mesh = get_mesh(mesh_index)

        # Change the mesh scale, rotation, and translation values per animation frame
        # (kept commented out, exactly like the C code)
        # rotate_mesh_x(mesh_index, mesh.rotation_velocity[0] * delta_time)
        # rotate_mesh_y(mesh_index, mesh.rotation_velocity[1] * delta_time)
        # rotate_mesh_z(mesh_index, mesh.rotation_velocity[2] * delta_time)

        # Process graphics pipeline stages for each mesh
        process_graphics_pipeline_stages(mesh)


###############################################################################
# Render function to draw objects on the display
###############################################################################
def render() -> None:
    """Clear the buffers, rasterize this frame's triangles, and present."""
    # Clear all the arrays to get ready for the next frame
    clear_color_buffer(0xFF000000)
    clear_z_buffer()

    draw_grid()

    # Loop all triangles from the triangles_to_render array
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
                triangle.points[0][0], triangle.points[0][1], triangle.points[0][2], triangle.points[0][3],
                triangle.texcoords[0].u, triangle.texcoords[0].v,  # vertex A
                triangle.points[1][0], triangle.points[1][1], triangle.points[1][2], triangle.points[1][3],
                triangle.texcoords[1].u, triangle.texcoords[1].v,  # vertex B
                triangle.points[2][0], triangle.points[2][1], triangle.points[2][2], triangle.points[2][3],
                triangle.texcoords[2].u, triangle.texcoords[2].v,  # vertex C
                triangle.texture,
            )

        # Draw triangle wireframe
        if should_render_wire():
            draw_triangle(
                int(triangle.points[0][0]), int(triangle.points[0][1]),  # vertex A
                int(triangle.points[1][0]), int(triangle.points[1][1]),  # vertex B
                int(triangle.points[2][0]), int(triangle.points[2][1]),  # vertex C
                0xFFFFFFFF,
            )

        # Draw triangle vertex points.
        # Color note: main.c writes 0xFF0000FF, but the C build presents its
        # buffer as RGBA32, so those squares show up RED on screen. Our buffer
        # is true ARGB (0xAARRGGBB), so red is 0xFFFF0000 — matching what the
        # C program actually displays.
        if should_render_wire_vertex():
            draw_rect(int(triangle.points[0][0]) - 3, int(triangle.points[0][1]) - 3, 6, 6, 0xFFFF0000)  # vertex A
            draw_rect(int(triangle.points[1][0]) - 3, int(triangle.points[1][1]) - 3, 6, 6, 0xFFFF0000)  # vertex B
            draw_rect(int(triangle.points[2][0]) - 3, int(triangle.points[2][1]) - 3, 6, 6, 0xFFFF0000)  # vertex C

    # Finally draw the color buffer to the SDL window
    render_color_buffer()


###############################################################################
# Free the memory that was dynamically allocated by the program
###############################################################################
def free_resources() -> None:
    """Release the meshes and shut the window down."""
    free_meshes()
    destroy_window()


###############################################################################
# Main function
###############################################################################
def main() -> None:
    """Entry point: init, setup, then the process-update-render loop."""
    global is_running

    is_running = init_window(fullscreen="--fullscreen" in sys.argv)

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

    free_resources()


if __name__ == "__main__":
    main()
