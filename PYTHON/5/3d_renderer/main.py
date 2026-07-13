"""Step 5 — first pixels: drawing a grid into the color buffer (mirrors src/main.c).

This is the step where the program draws something of its own for the first
time. ``draw_grid()`` writes gray pixels directly into the color buffer on
every 10th row and column — proof that "rendering" is now just writing
numbers into our own array. The clear color also changes from the step-3/4
debug yellow to black, and the redundant SDL renderer clear is removed (the
color buffer covers the whole window, so clearing the window twice was
wasted work).

C -> Python mapping:
    uint32_t* color_buffer (malloc)                  -> numpy uint32 array, shape (h, w)
    SDL_CreateTexture(ARGB8888, STREAMING)           -> not needed; pygame blits a Surface built from the buffer
    SDL_UpdateTexture + SDL_RenderCopy               -> pygame.image.frombuffer(..., "BGRA") + window.blit
    SDL_RenderPresent                                -> pygame.display.flip()
    free + SDL_DestroyRenderer/Window + SDL_Quit     -> destroy_window() -> pygame.quit()

Pixel format trick (CONVENTIONS.md §4): the buffer keeps the exact C color
literals (0xAARRGGBB). Viewed as raw bytes on a little-endian machine those
are ordered BB GG RR AA — which pygame calls "BGRA" — so presenting is one
``pygame.image.frombuffer`` call, no channel shuffling.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pygame

import hud


# Key bindings shown by the on-screen help (press H). Derived from the
# actual handlers in process_input below.
KEY_BINDINGS: list[tuple[str, str]] = [
    ("ESC", "quit"),
]
hud.init_hud(KEY_BINDINGS)
# Module-level state — mirrors the globals at the top of main.c.
is_running: bool = False
window: pygame.Surface | None = None

color_buffer: np.ndarray | None = None
# C also keeps an SDL_Texture* (color_buffer_texture); pygame needs no
# separate streaming texture — see render_color_buffer().

window_width: int = 800
window_height: int = 600


def initialize_window() -> bool:
    """Initialize SDL (pygame) and open the window.

    Mirrors initialize_window() in main.c: SDL_Init, SDL_CreateWindow,
    SDL_CreateRenderer, each with an error check. pygame creates the window
    and its renderer together in ``set_mode``, so the two C error paths
    collapse into one here.

    The C code calls SDL_GetCurrentDisplayMode(0, ...) and sets
    window_width/window_height to the full desktop resolution before
    creating a borderless window. Deviation (CONVENTIONS.md §7): the Python
    default stays a normal framed 800x600 window (friendlier for
    development); pass ``--fullscreen`` on the command line to get the C
    behavior. The rendering logic is unaffected either way.
    """
    global window, window_width, window_height

    pygame.init()
    if not pygame.display.get_init():
        print("Error initializing SDL.")
        return False

    fullscreen = "--fullscreen" in sys.argv[1:]
    if fullscreen:
        # C: SDL_GetCurrentDisplayMode -> window_width/height = desktop size.
        # pygame.display.Info() reports the current display mode; guard the
        # dummy video driver, which reports no real resolution (w/h <= 0).
        display_info = pygame.display.Info()
        if display_info.current_w > 0 and display_info.current_h > 0:
            window_width = display_info.current_w
            window_height = display_info.current_h

    # SDL_WINDOWPOS_CENTERED is pygame's default placement.
    flags = pygame.NOFRAME if fullscreen else 0  # C: SDL_WINDOW_BORDERLESS
    window = pygame.display.set_mode((window_width, window_height), flags)
    if window is None:
        print("Error creating SDL window.")
        return False

    return True


def setup() -> None:
    """Allocate the color buffer (C: malloc + SDL_CreateTexture).

    Mirrors setup() in main.c. The C code mallocs window_width *
    window_height uint32 pixels and creates an ARGB8888 streaming texture to
    display them. Here the buffer is a numpy uint32 array of shape
    (height, width) holding the same 0xAARRGGBB values; no separate texture
    object is needed because render_color_buffer() builds a pygame Surface
    straight from the buffer's bytes.

    Improvement (CONVENTIONS.md §10): np.zeros initializes the buffer to
    black, where C's malloc leaves it uninitialized (the C first frame shows
    garbage memory).
    """
    global color_buffer

    color_buffer = np.zeros((window_height, window_width), dtype=np.uint32)


def process_input() -> None:
    """Poll events; quit on window close or the ESC key.

    Mirrors process_input() in main.c. Improvement (CONVENTIONS.md §10):
    the C code polls a single event per frame, which lags when events queue
    up; here we drain the whole queue each frame — same behavior, no lag.
    """
    global is_running

    for event in pygame.event.get():
        hud.handle_event(event)  # H toggles the key-bindings help
        if event.type == pygame.QUIT:
            is_running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                is_running = False


def update() -> None:
    """Mirrors update() in main.c — still an empty TODO at this step."""
    # TODO:


def draw_grid() -> None:
    """Draw gray lines on every 10th row and column of the color buffer.

    Mirrors draw_grid() in main.c, which loops over ALL width x height
    pixels and tests ``x % 10 == 0 || y % 10 == 0``. Performance
    (CONVENTIONS.md §5): that modulo test selects entire rows and columns,
    so two strided numpy slice assignments write exactly the same pixels —
    480,000 loop iterations become 2 array operations.
    """
    assert color_buffer is not None
    color_buffer[::10, :] = 0xFF888888  # every 10th row    (y % 10 == 0)
    color_buffer[:, ::10] = 0xFF888888  # every 10th column (x % 10 == 0)


def render_color_buffer() -> None:
    """Copy the color buffer to the window (C: SDL_UpdateTexture + SDL_RenderCopy).

    The uint32 0xAARRGGBB buffer is viewed as raw bytes; on a little-endian
    machine those bytes are ordered BB GG RR AA, which pygame calls "BGRA".
    """
    assert color_buffer is not None and window is not None
    surface = pygame.image.frombuffer(
        color_buffer.tobytes(), (window_width, window_height), "BGRA"
    )
    window.blit(surface, (0, 0))


def clear_color_buffer(color: int) -> None:
    """Fill the whole color buffer with one color.

    Mirrors clear_color_buffer() in main.c. Performance (CONVENTIONS.md §5):
    the C double loop over every pixel becomes a single numpy broadcast
    assignment — no per-pixel Python loop.
    """
    assert color_buffer is not None
    color_buffer[:] = color


def render() -> None:
    """Draw the grid, present the color buffer, then clear it for the next frame.

    Mirrors render() in main.c, in the same order:
    draw_grid() -> write the grid pixels into the buffer,
    render_color_buffer() -> show the buffer,
    clear_color_buffer(0xFF000000) -> reset the buffer to black,
    SDL_RenderPresent -> flip.

    (Step 5 removed the SDL_SetRenderDrawColor + SDL_RenderClear pair the
    earlier steps had — the color buffer already covers every window pixel,
    so clearing the window separately was redundant.)
    """
    draw_grid()
    render_color_buffer()
    clear_color_buffer(0xFF000000)

    hud.draw(window)  # on-screen key help (H)
    pygame.display.flip()


def destroy_window() -> None:
    """Free resources and shut SDL down (C: free + SDL_Destroy* + SDL_Quit).

    Mirrors destroy_window() in main.c. Python's garbage collector frees the
    numpy buffer; pygame.quit() tears down the window and renderer.
    """
    pygame.quit()


def main() -> None:
    """Mirrors main() in main.c: init, setup, game loop, destroy_window."""
    global is_running

    is_running = initialize_window()

    setup()

    # Test hooks (CONVENTIONS.md §7) — identical block in every step:
    # RENDERER_MAX_FRAMES=<n> exits cleanly after n frames;
    # RENDERER_SAVE_FRAME=<path.png> saves the final frame on exit.
    max_frames = int(os.environ.get("RENDERER_MAX_FRAMES", "0"))
    save_frame_path = os.environ.get("RENDERER_SAVE_FRAME", "")
    frame_count = 0

    while is_running:
        process_input()
        update()
        render()

        frame_count += 1
        if max_frames and frame_count >= max_frames:
            is_running = False

    if save_frame_path and window is not None:
        pygame.image.save(window, save_frame_path)

    destroy_window()


if __name__ == "__main__":
    main()
