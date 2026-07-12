"""Step 2 — First SDL window (mirrors src/main.c).

This step replaces the Hello-World console program with the skeleton every
later step builds on: initialize a window, then spin the classic game loop
(process_input -> update -> render) until the user quits. The C code clears
the screen to solid red through the SDL renderer and presents it — there is
no CPU-side color buffer yet (that arrives in a later step), so this port
needs pygame only, no numpy.

C -> Python mapping:
    SDL_Init / SDL_CreateWindow / SDL_CreateRenderer  -> pygame.init() + pygame.display.set_mode()
    SDL_SetRenderDrawColor + SDL_RenderClear          -> window.fill((r, g, b))
    SDL_RenderPresent                                 -> pygame.display.flip()
"""

from __future__ import annotations

import os

import pygame

WINDOW_WIDTH: int = 800
WINDOW_HEIGHT: int = 600

# Module-level state — mirrors the globals at the top of main.c.
is_running: bool = False
window: pygame.Surface | None = None


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
    window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    if window is None:
        print("Error creating SDL window.")
        return False

    return True


def setup() -> None:
    """Mirrors setup() in main.c — still an empty TODO at this step."""
    # TODO:


def process_input() -> None:
    """Poll events; quit on window close or the ESC key.

    Mirrors process_input() in main.c. Improvement (CONVENTIONS.md §10):
    the C code polls a single event per frame, which lags when events queue
    up; here we drain the whole queue each frame — same behavior, no lag.
    """
    global is_running

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            is_running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                is_running = False


def update() -> None:
    """Mirrors update() in main.c — still an empty TODO at this step."""
    # TODO:


def render() -> None:
    """Clear the screen to solid red and present it.

    Mirrors render() in main.c: SDL_SetRenderDrawColor(renderer, 255, 0, 0,
    255) + SDL_RenderClear + SDL_RenderPresent.
    """
    assert window is not None
    window.fill((255, 0, 0))
    pygame.display.flip()


def main() -> None:
    """Mirrors main() in main.c: init, setup, then the game loop."""
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

    pygame.quit()


if __name__ == "__main__":
    main()
