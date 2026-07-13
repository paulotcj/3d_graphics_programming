"""Step 3 — CPU-side color buffer (mirrors src/main.c).

This step introduces the heart of the whole software renderer: a CPU-side
**color buffer** — one uint32 per pixel in ARGB8888 format — that the code
clears itself and then hands to SDL to display. From here on, "rendering"
means writing pixels into this array; SDL is only the delivery mechanism.

C -> Python mapping:
    uint32_t* color_buffer (malloc)      -> numpy uint32 array, shape (h, w)
    SDL_CreateTexture(ARGB8888, STREAMING) + SDL_UpdateTexture + SDL_RenderCopy
                                         -> pygame.image.frombuffer(..., "BGRA") + blit
    clear_color_buffer double loop       -> color_buffer[:] = color  (one numpy fill)

The buffer keeps the exact C color literals (0xAARRGGBB): viewed as raw
bytes on a little-endian machine, a uint32 0xAARRGGBB is BB GG RR AA in
memory, which pygame calls "BGRA" (CONVENTIONS.md §4).
"""

from __future__ import annotations

import os

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

window_width: int = 800
window_height: int = 600


def initialize_window() -> bool:
    """Initialize SDL (pygame) and open the 800x600 centered window.

    Mirrors initialize_window() in main.c: SDL_Init, SDL_CreateWindow,
    SDL_CreateRenderer, each with an error check. pygame creates the window
    and its renderer together in ``set_mode``, so the two C error paths
    collapse into one here.

    Deviation (CONVENTIONS.md §7): the C window is SDL_WINDOW_BORDERLESS;
    the Python default is a normal framed window, which is friendlier for
    development. The size, position, and rendering are identical.
    """
    global window

    pygame.init()
    if not pygame.display.get_init():
        print("Error initializing SDL.")
        return False

    # SDL_WINDOWPOS_CENTERED is pygame's default placement.
    window = pygame.display.set_mode((window_width, window_height))
    if window is None:
        print("Error creating SDL window.")
        return False

    return True


def setup() -> None:
    """Allocate the color buffer (C: malloc + SDL_CreateTexture).

    Mirrors setup() in main.c. The C code mallocs window_width *
    window_height uint32s and creates a streaming ARGB8888 SDL texture to
    display them. Here the buffer is a numpy uint32 array of shape
    (height, width); no separate texture object is needed — the buffer is
    converted to a pygame surface on the fly in render_color_buffer().

    (C's malloc leaves the buffer uninitialized; numpy zero-fills, so the
    very first frame is black instead of undefined garbage.)
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
    """Fill the whole color buffer with one 0xAARRGGBB color.

    Mirrors clear_color_buffer() in main.c. The C double loop over every
    pixel becomes a single numpy broadcast fill (CONVENTIONS.md §5).
    """
    assert color_buffer is not None
    color_buffer[:] = color


def render() -> None:
    """Present the color buffer, then clear it for the next frame.

    Mirrors render() in main.c, in the same order the C code uses:
    clear the backbuffer to black, copy the color buffer to the screen,
    clear the color buffer to yellow (0xFFFFFF00, ARGB), and present.
    Note the C code clears *after* copying, so each frame shows the buffer
    as it was left by the previous frame — a solid yellow screen.
    """
    assert window is not None
    # SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255) + SDL_RenderClear
    window.fill((0, 0, 0))

    render_color_buffer()
    # Remember: We are using the format alpha red green blue
    clear_color_buffer(0xFFFFFF00)

    # SDL_RenderPresent
    hud.draw(window)  # on-screen key help (H)
    pygame.display.flip()


def destroy_window() -> None:
    """Free resources and shut SDL down (C: free + SDL_Destroy* + SDL_Quit).

    Mirrors destroy_window() in main.c. Python's garbage collector frees the
    numpy buffer; pygame.quit() tears down the window and renderer.
    """
    pygame.quit()


def main() -> None:
    """Mirrors main() in main.c: init, setup, game loop, teardown."""
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
