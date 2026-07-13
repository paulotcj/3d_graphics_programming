"""display.py — mirrors src/display.c of C step 9.

Step 9 is a pure refactor: the window/renderer globals and every drawing
helper move out of main.c into this new display.c/display.h pair. This module
owns the pygame window, the CPU-side color buffer, the window dimensions, and
the drawing helpers (grid, rect, present, clear) — main.py keeps the game
loop, exactly as in C.

Pixel format (CONVENTIONS.md §4): ``color_buffer`` is a NumPy ``uint32``
array of shape ``(window_height, window_width)`` holding ``0xAARRGGBB``
values — the exact same literals the C code writes. To present it, the
buffer bytes are handed to pygame as "BGRA", because a little-endian
``0xAARRGGBB`` uint32 is the byte sequence BB GG RR AA in memory.

Every per-pixel C loop is re-expressed as a NumPy array operation
(CONVENTIONS.md §5) — see the comment on each drawing function.
"""

from __future__ import annotations

import sys

import numpy as np
import pygame

import hud

# Module-level state — mirrors the globals at the top of display.c
# (declared `extern` in display.h so main.c can see them). Note that
# color_buffer is *allocated* by main.py's setup(), just as in the C code.
window: pygame.Surface | None = None
color_buffer: np.ndarray | None = None  # (h, w) uint32, 0xAARRGGBB
window_width: int = 800
window_height: int = 600


def initialize_window(fullscreen: bool = False) -> bool:
    """Initialize pygame, open the window, and create the drawing surface.

    The C code queries the desktop resolution and opens a borderless window
    covering it. Per CONVENTIONS.md §7 the Python default is a friendlier
    800x600 centered window; pass ``fullscreen=True`` (the ``--fullscreen``
    flag) for the original C behavior.
    """
    global window, window_width, window_height

    pygame.init()
    if not pygame.display.get_init():
        print("Error initializing SDL.", file=sys.stderr)
        return False

    if fullscreen:
        # Mirror the C code: SDL_GetCurrentDisplayMode -> borderless window.
        # Guarded so SDL_VIDEODRIVER=dummy (no real resolution) keeps 800x600.
        info = pygame.display.Info()
        if info.current_w > 0 and info.current_h > 0:
            window_width = info.current_w
            window_height = info.current_h
        window = pygame.display.set_mode((window_width, window_height), pygame.NOFRAME)
    else:
        window = pygame.display.set_mode((window_width, window_height))
    pygame.display.set_caption("3D Renderer")

    return True


def draw_grid() -> None:
    """Draw a gray dot every 10 pixels in both axes.

    C: a nested loop stepping x and y by 10. NumPy: one strided slice
    assignment touches exactly the same pixels (CONVENTIONS.md §5).
    """
    assert color_buffer is not None
    color_buffer[::10, ::10] = 0xFFAAAAAA


def draw_rect(x: int, y: int, width: int, height: int, color: int) -> None:
    """Fill a rectangle with a solid color.

    C: a double loop over width x height writing one pixel at a time.
    NumPy: one 2-D slice assignment (CONVENTIONS.md §5). Bounds are clamped
    to the screen (the C code has no clamp; the step's one call site fits
    on screen).
    """
    assert color_buffer is not None

    x_start, y_start = max(x, 0), max(y, 0)
    x_end, y_end = min(x + width, window_width), min(y + height, window_height)
    if x_start >= x_end or y_start >= y_end:
        return
    color_buffer[y_start:y_end, x_start:x_end] = color


def render_color_buffer() -> None:
    """Present the color buffer in the window (C: SDL_UpdateTexture + RenderCopy).

    The uint32 0xAARRGGBB buffer is viewed as raw bytes; on a little-endian
    machine those bytes are ordered BB GG RR AA, which pygame calls "BGRA".
    ``convert()`` drops the per-pixel alpha channel so the blit copies the
    RGB values verbatim — matching SDL's default no-blending texture copy.
    """
    assert color_buffer is not None and window is not None
    surface = pygame.image.frombuffer(
        color_buffer.tobytes(), (window_width, window_height), "BGRA"
    ).convert()
    window.blit(surface, (0, 0))
    hud.draw(window)  # on-screen key help (H)
    pygame.display.flip()


def clear_color_buffer(color: int) -> None:
    """Fill the whole color buffer with one color (C: a full-buffer loop).

    NumPy: a single broadcast assignment (CONVENTIONS.md §5).
    """
    assert color_buffer is not None
    color_buffer[:] = color


def destroy_window() -> None:
    """Shut pygame down (C: free + SDL_Destroy* + SDL_Quit)."""
    pygame.quit()
