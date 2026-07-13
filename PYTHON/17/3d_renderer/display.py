"""display.py — mirrors src/display.c and src/display.h.

Owns the pygame window, the CPU-side color buffer, and the primitive drawing
helpers this step uses (grid, pixel, rect).

Pixel format (CONVENTIONS.md §4): ``color_buffer`` is a NumPy ``uint32``
array of shape ``(window_height, window_width)`` holding ``0xAARRGGBB``
values — the exact same literals the C code writes. To present it, the
buffer bytes are handed to pygame as "BGRA", because a little-endian
``0xAARRGGBB`` uint32 is the byte sequence BB GG RR AA in memory.

Every per-pixel C loop in this file is re-expressed as a NumPy array
operation (CONVENTIONS.md §5) — see the comment on each drawing function.
"""

from __future__ import annotations

import numpy as np
import pygame

import hud

# Frame-rate cap — mirrors the new #defines in display.h (step 16):
#   #define FPS 60
#   #define FRAME_TARGET_TIME (1000 / FPS)
FPS: int = 60
FRAME_TARGET_TIME: int = 1000 // FPS  # milliseconds per frame

# Module-level state — mirrors the globals at the top of display.c.
window: pygame.Surface | None = None
color_buffer: np.ndarray | None = None  # (h, w) uint32, 0xAARRGGBB
window_width: int = 800
window_height: int = 600


def initialize_window(fullscreen: bool = False) -> bool:
    """Initialize pygame, open the window, and allocate the color buffer.

    The C code opens a borderless window at the full desktop resolution.
    Per CONVENTIONS.md §7 the Python default is a friendlier 800x600 window;
    pass ``fullscreen=True`` (the ``--fullscreen`` flag) for the C behavior.
    """
    global window, color_buffer, window_width, window_height

    pygame.init()
    if not pygame.display.get_init():
        print("Error initializing SDL.")
        return False

    if fullscreen:
        # Mirror the C code: query the desktop resolution and open a
        # borderless window covering it. Guarded so SDL_VIDEODRIVER=dummy
        # (which reports no real resolution) falls back to 800x600.
        info = pygame.display.Info()
        if info.current_w > 0 and info.current_h > 0:
            window_width = info.current_w
            window_height = info.current_h
        window = pygame.display.set_mode((window_width, window_height), pygame.NOFRAME)
    else:
        window = pygame.display.set_mode((window_width, window_height))
    pygame.display.set_caption("3D Renderer")

    # Allocate the color buffer (C: malloc in setup(); here it lives with the
    # window because pygame needs the mode set before the size is final).
    color_buffer = np.zeros((window_height, window_width), dtype=np.uint32)

    return True


def draw_grid() -> None:
    """Draw a dot every 10 pixels in both axes.

    C: a nested loop stepping x and y by 10. NumPy: one strided slice
    assignment touches exactly the same pixels (CONVENTIONS.md §5).
    """
    assert color_buffer is not None
    color_buffer[::10, ::10] = 0xFFAAAAAA


def draw_pixel(x: int, y: int, color: int) -> None:
    """Set a single pixel, ignoring coordinates outside the window.

    Imagine that ``window_width * y`` in the C code means "y fully completed
    rows"; the 2-D NumPy index ``[y, x]`` expresses the same location.
    """
    if x < 0 or x >= window_width or y < 0 or y >= window_height:
        return
    assert color_buffer is not None
    color_buffer[y, x] = color


def draw_rect(x: int, y: int, width: int, height: int, color: int) -> None:
    """Fill a solid rectangle.

    C: a double loop over width x height calling draw_pixel. NumPy: clamp the
    rectangle to the screen and assign one 2-D slice (CONVENTIONS.md §5).
    """
    assert color_buffer is not None
    x, y = int(x), int(y)

    x_start = max(x, 0)
    y_start = max(y, 0)
    x_end = min(x + width, window_width)
    y_end = min(y + height, window_height)
    if x_start >= x_end or y_start >= y_end:
        return
    color_buffer[y_start:y_end, x_start:x_end] = color


def render_color_buffer() -> None:
    """Present the color buffer in the window.

    C: SDL_UpdateTexture + SDL_RenderCopy (the SDL_RenderPresent happens at
    the end of render() in main.c; pygame's flip here covers both).
    The uint32 0xAARRGGBB buffer is viewed as raw bytes; on a little-endian
    machine those bytes are ordered BB GG RR AA, which pygame calls "BGRA".
    """
    assert color_buffer is not None and window is not None
    surface = pygame.image.frombuffer(
        color_buffer.tobytes(), (window_width, window_height), "BGRA"
    )
    window.blit(surface, (0, 0))
    hud.draw(window)  # on-screen key help (H)
    pygame.display.flip()


def clear_color_buffer(color: int) -> None:
    """Fill the whole color buffer with one color (C: a full-buffer loop)."""
    assert color_buffer is not None
    color_buffer[:] = color


def destroy_window() -> None:
    """Shut pygame down (C: free buffer + SDL_Destroy* + SDL_Quit)."""
    pygame.quit()
