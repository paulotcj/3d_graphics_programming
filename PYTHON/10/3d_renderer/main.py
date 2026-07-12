"""main.py — mirrors src/main.c of C step 9.

Step 9 refactors step 8 without changing what is drawn: the window globals
and all drawing helpers move out of main.c into a new display.c/display.h
pair (here: ``display.py``). main.c keeps only the game loop — setup,
process_input, update, render — and calls into the display module. The image
is identical to step 8: a gray 10-pixel dot grid with a solid magenta
300x150 rectangle at (300, 200).

See display.py for the pixel-format trick (CONVENTIONS.md §4) and the NumPy
replacements for every per-pixel C loop (CONVENTIONS.md §5).
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pygame

import display
from display import (
    clear_color_buffer,
    destroy_window,
    draw_grid,
    draw_rect,
    initialize_window,
    render_color_buffer,
)

FPS: int = 60  # CONVENTIONS.md §7 frame cap (the C step 9 loop is uncapped; see README)

# Module-level state — mirrors the lone global left at the top of main.c.
is_running: bool = False


def setup() -> None:
    """Allocate the color buffer (C: malloc + SDL_CreateTexture).

    As in C — where main.c's setup() assigns the ``extern`` color_buffer
    declared in display.h — the buffer lives in the display module but is
    allocated here. pygame needs no explicit streaming texture:
    ``render_color_buffer`` builds a surface straight from the buffer bytes
    every frame.
    """
    display.color_buffer = np.zeros(
        (display.window_height, display.window_width), dtype=np.uint32
    )


def process_input() -> None:
    """Handle quit and ESC.

    The C code polls a single event per frame (``SDL_PollEvent`` once),
    which makes input laggy when events queue up. Draining the whole queue
    with a loop is a documented allowed fix (CONVENTIONS.md §10).
    """
    global is_running
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            is_running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                is_running = False


def update() -> None:
    """Nothing to update yet (C: an empty TODO body)."""


def render() -> None:
    """Draw one frame: grid + magenta rect, present, then clear for the next."""
    assert display.window is not None
    # C: SDL_SetRenderDrawColor(0,0,0,255) + SDL_RenderClear. The full-window
    # blit in render_color_buffer overwrites everything anyway; kept for parity.
    display.window.fill((0, 0, 0))

    draw_grid()

    draw_rect(300, 200, 300, 150, 0xFFFF00FF)

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

        clock.tick(FPS)  # CONVENTIONS.md §7 frame cap (C step 9 has none)

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
