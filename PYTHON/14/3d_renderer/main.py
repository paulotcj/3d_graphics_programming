"""main.py — mirrors src/main.c of C step 12.

Step 12 is the "aha" moment of the course: **perspective projection**.
``project()`` now divides x and y by the point's z — the similar-triangles
rule that makes far things small — and a ``camera_position`` at z = -5 pushes
the cloud away from the viewer (each point's z becomes point.z + 5, i.e.
4..6). On screen the flat square of step 11 turns into a cube seen head-on:
the near 9x9 face projects large, the far face small, and the in-between
layers nest inside each other.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pygame

import hud

import display
from display import (
    clear_color_buffer,
    destroy_window,
    draw_grid,
    draw_rect,
    initialize_window,
    render_color_buffer,
)
from vector import Vec2, Vec3, vec2_new, vec3_new


# Key bindings shown by the on-screen help (press H). Derived from the
# actual handlers in process_input below.
KEY_BINDINGS: list[tuple[str, str]] = [
    ("ESC", "quit"),
]
hud.init_hud(KEY_BINDINGS)
FPS: int = 60  # CONVENTIONS.md §7 frame cap (the C step 10 loop is uncapped; see README)

###############################################################################
# Declare an array of vectors/points
###############################################################################
N_POINTS: int = 9 * 9 * 9

cube_points: list[Vec3] = []  # C: vec3_t cube_points[N_POINTS] — 9x9x9 cube
projected_points: list[Vec2] = []  # C: vec2_t projected_points[N_POINTS]

camera_position: Vec3 = vec3_new(0, 0, -5)

fov_factor: float = 640

is_running: bool = False


def setup() -> None:
    """Allocate the color buffer and build the 9x9x9 point cloud.

    Mirrors setup() in main.c: after allocating the buffer, three nested
    loops walk x, y, z from -1 to 1 in steps of 0.25 (9 values per axis) and
    store a vec3 for every combination. np.arange replaces the C float
    loops; the visiting order (x outer, z inner) is identical.
    """
    display.color_buffer = np.zeros(
        (display.window_height, display.window_width), dtype=np.uint32
    )

    # From -1 to 1 (in this 9x9x9 cube)
    axis = np.arange(-1.0, 1.0 + 0.25, 0.25)  # [-1, -0.75, ..., 1] — 9 values
    for x in axis:
        for y in axis:
            for z in axis:
                cube_points.append(vec3_new(x, y, z))


def process_input() -> None:
    """Handle quit and ESC.

    The C code polls a single event per frame (``SDL_PollEvent`` once),
    which makes input laggy when events queue up. Draining the whole queue
    with a loop is a documented allowed fix (CONVENTIONS.md §10).
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
    """Perspective-project a 3D point to 2D: scale by FOV, divide by depth.

    Mirrors project() in main.c (step 12's version). The rule comes from
    similar triangles — for a viewer at the origin looking down +z, a point
    twice as far away appears half as high:

        BC/DE == AB/AD  ->  X'/X == 1/Z  ->  X' = X/Z   (same for Y)

    fov_factor (now 640) converts the small X/Z ratio to pixels.
    """
    return vec2_new(
        (fov_factor * point[0]) / point[2],
        (fov_factor * point[1]) / point[2],
    )


def update() -> None:
    """Project every cube point into projected_points (mirrors update())."""
    projected_points.clear()
    for point in cube_points:
        # Move the points away from the camera (camera sits at z = -5, so
        # every point's depth becomes point.z - (-5) = point.z + 5).
        moved_point = point.copy()
        moved_point[2] -= camera_position[2]

        projected_point = project(moved_point)
        projected_points.append(projected_point)


def render() -> None:
    """Draw the dot grid and a 4x4 rectangle per projected point, then present."""
    draw_grid()

    # Loop all projected points and render them, offset to the screen center
    for projected_point in projected_points:
        draw_rect(
            int(projected_point[0]) + (display.window_width // 2),
            int(projected_point[1]) + (display.window_height // 2),
            4,
            4,
            0xFFFFFF00,
        )

    render_color_buffer()

    clear_color_buffer(0xFF000000)


def main() -> None:
    """Game loop: process_input -> update -> render, exactly as in main.c."""
    global is_running

    is_running = initialize_window(fullscreen="--fullscreen" in sys.argv)

    setup()

    # --- Test hooks (CONVENTIONS.md §7) — identical block in every step. ---
    max_frames_env = os.environ.get("RENDERER_MAX_FRAMES")
    max_frames = int(max_frames_env) if max_frames_env else None
    save_frame_path = os.environ.get("RENDERER_SAVE_FRAME")
    frame_count = 0
    # -----------------------------------------------------------------------

    clock = pygame.time.Clock()

    while is_running:
        process_input()
        update()
        render()

        clock.tick(FPS)  # CONVENTIONS.md §7 frame cap (C step 10 has none)

        # --- Test hooks (CONVENTIONS.md §7) ---
        frame_count += 1
        if max_frames is not None and frame_count >= max_frames:
            is_running = False
        # --------------------------------------

    # --- Test hooks (CONVENTIONS.md §7): save the last presented frame. ---
    if save_frame_path and display.window is not None:
        pygame.image.save(display.window, save_frame_path)
    # -----------------------------------------------------------------------

    destroy_window()


if __name__ == "__main__":
    main()
