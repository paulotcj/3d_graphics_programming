"""Step 16 — Fixed frame rate (mirrors src/main.c).

Same spinning 9x9x9 point cloud as step 15, but the game loop is now capped
at a fixed frame rate: the C code adds ``FPS``/``FRAME_TARGET_TIME`` to
display.h and busy-waits at the top of ``update()`` until
``FRAME_TARGET_TIME`` milliseconds have passed since the previous frame, so
the rotation speed no longer depends on how fast the machine is.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pygame

import hud

import display
from vector import Vec2, Vec3, vec3_rotate_x, vec3_rotate_y, vec3_rotate_z


# Key bindings shown by the on-screen help (press H). Derived from the
# actual handlers in process_input below.
KEY_BINDINGS: list[tuple[str, str]] = [
    ("ESC", "quit"),
]
hud.init_hud(KEY_BINDINGS)
###############################################################################
# Declare an array of vectors/points
###############################################################################
N_POINTS: int = 9 * 9 * 9
cube_points: list[Vec3] = []  # 9x9x9 cube
projected_points: list[Vec2] = []

camera_position: Vec3 = np.array([0.0, 0.0, -5.0], dtype=np.float64)
cube_rotation: Vec3 = np.array([0.0, 0.0, 0.0], dtype=np.float64)

fov_factor: float = 640.0

is_running: bool = False

# Frame-rate cap (new in this step): the C code adds a global
# ``previous_frame_time`` and busy-waits at the top of update() until
# FRAME_TARGET_TIME milliseconds have passed. pygame's Clock.tick(FPS) waits
# for the exact same 60 FPS target without burning a CPU core (documented
# improvement); FPS and FRAME_TARGET_TIME live in display.py, mirroring the
# new #defines in display.h.
clock: pygame.time.Clock | None = None


def setup() -> None:
    """Fill cube_points with the 9x9x9 grid spanning -1..1 on each axis.

    The color buffer the C code mallocs here is allocated in
    display.initialize_window() (pygame needs the window first).
    """
    del cube_points[:]
    del projected_points[:]

    # Start loading the array of vectors, from -1 to 1 in steps of 0.25
    # (np.linspace avoids the C float-accumulation loop's rounding drift).
    values = np.linspace(-1.0, 1.0, 9)
    for x in values:
        for y in values:
            for z in values:
                cube_points.append(np.array([x, y, z], dtype=np.float64))
    projected_points.extend(np.zeros(2, dtype=np.float64) for _ in range(N_POINTS))


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
    """Cap the frame rate, then rotate, translate, and project every point.

    C (new in this step)::

        while (!SDL_TICKS_PASSED(SDL_GetTicks(), previous_frame_time + FRAME_TARGET_TIME));
        previous_frame_time = SDL_GetTicks();

    Clock.tick sleeps until FRAME_TARGET_TIME milliseconds have elapsed since
    the previous call — the same fixed 60 FPS pacing as the C busy-wait,
    minus the 100% CPU spin (so ``previous_frame_time`` bookkeeping is not
    needed here).
    """
    assert clock is not None
    clock.tick(display.FPS)

    cube_rotation[0] += 0.01
    cube_rotation[1] += 0.01
    cube_rotation[2] += 0.01

    for i in range(N_POINTS):
        point = cube_points[i]

        transformed_point = vec3_rotate_x(point, cube_rotation[0])
        transformed_point = vec3_rotate_y(transformed_point, cube_rotation[1])
        transformed_point = vec3_rotate_z(transformed_point, cube_rotation[2])

        # Move the points away from the camera
        transformed_point[2] -= camera_position[2]

        # Project the current point and save the resulting 2D vector
        projected_points[i] = project(transformed_point)


def render() -> None:
    """Draw the grid and every projected point, then present the frame."""
    display.draw_grid()

    # Loop all projected points and render them as 4x4 yellow rectangles,
    # translated to the center of the screen.
    for i in range(N_POINTS):
        projected_point = projected_points[i]
        display.draw_rect(
            int(projected_point[0] + (display.window_width / 2)),
            int(projected_point[1] + (display.window_height / 2)),
            4,
            4,
            0xFFFFFF00,
        )

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
