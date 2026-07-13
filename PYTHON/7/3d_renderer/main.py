"""main.py — mirrors src/main.c of C step 7 (the only C file in this step).

Step 7 builds on the color-buffer machinery from step 6 and adds the first
real drawing function: ``draw_rect``. The C version of ``draw_rect`` has a
deliberate quirk (it ignores the color you pass in and paints a per-column
gradient instead) which is reproduced here exactly — the C code is ground
truth for this step's behavior.

Pixel format (CONVENTIONS.md §4): ``color_buffer`` is a NumPy ``uint32``
array of shape ``(window_height, window_width)`` holding ``0xAARRGGBB``
values — the exact same literals the C code writes. To present it, the
buffer bytes are handed to pygame as "BGRA", because a little-endian
``0xAARRGGBB`` uint32 is the byte sequence BB GG RR AA in memory.

Every per-pixel C loop is re-expressed as a NumPy array operation
(CONVENTIONS.md §5) — see the comment on each drawing function.
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
FPS: int = 60  # CONVENTIONS.md §7 frame cap (the C step 7 loop is uncapped; see README)

# Module-level state — mirrors the globals at the top of main.c.
is_running: bool = False
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


def setup() -> None:
    """Allocate the color buffer (C: malloc + SDL_CreateTexture).

    pygame needs no explicit streaming texture — ``render_color_buffer``
    builds a surface straight from the buffer bytes every frame.
    """
    global color_buffer
    color_buffer = np.zeros((window_height, window_width), dtype=np.uint32)


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


def update() -> None:
    """Nothing to update yet (C: an empty TODO body)."""


def draw_grid() -> None:
    """Draw a white dot every 10 pixels in both axes.

    C: a nested loop stepping x and y by 10. NumPy: one strided slice
    assignment touches exactly the same pixels (CONVENTIONS.md §5).
    """
    assert color_buffer is not None
    color_buffer[::10, ::10] = 0xFFFFFFFF


def draw_rect(x: int, y: int, width: int, height: int, color: int) -> None:
    """Fill a rectangle — with this step's C quirk preserved exactly.

    The C function *ignores* the ``color`` argument: it resets ``color`` to 0
    and then adds 1 before painting each column, so column ``i`` (0-based) of
    the rectangle is filled with the raw uint32 value ``i + 1``. That paints
    a barely-visible dark-blue gradient (values 0x00000001..0x0000012C for a
    300-pixel-wide rect), and that is what this port draws too.

    C: a double loop over width x height writing one pixel at a time.
    NumPy: build the per-column color ramp once with ``np.arange`` and
    broadcast it across the rectangle's rows in a single 2-D slice
    assignment (CONVENTIONS.md §5). Bounds are clamped to the screen
    (the C code has no clamp; the step's one call site fits on screen).
    """
    assert color_buffer is not None

    # C quirk: `color = start_color;` then `color = color + 1` per column.
    del color  # the argument is dead in the C code too
    column_colors = np.arange(1, width + 1, dtype=np.uint32)

    x_start, y_start = max(x, 0), max(y, 0)
    x_end, y_end = min(x + width, window_width), min(y + height, window_height)
    if x_start >= x_end or y_start >= y_end:
        return
    color_buffer[y_start:y_end, x_start:x_end] = column_colors[x_start - x : x_end - x]


def render_color_buffer() -> None:
    """Present the color buffer in the window (C: SDL_UpdateTexture + RenderCopy).

    The uint32 0xAARRGGBB buffer is viewed as raw bytes; on a little-endian
    machine those bytes are ordered BB GG RR AA, which pygame calls "BGRA".
    ``convert()`` drops the per-pixel alpha channel so the blit copies the
    RGB values verbatim — matching SDL's default no-blending texture copy
    (this step's rect colors have alpha 0x00, which must NOT make them
    transparent).
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


def render() -> None:
    """Draw one frame: grid + gradient rect, present, then clear for the next."""
    assert window is not None
    # C: SDL_SetRenderDrawColor(0,0,0,255) + SDL_RenderClear. The full-window
    # blit in render_color_buffer overwrites everything anyway; kept for parity.
    window.fill((0, 0, 0))

    draw_grid()

    draw_rect(300, 200, 300, 150, 0xFFFF00FF)

    render_color_buffer()
    clear_color_buffer(0xFF000000)


def destroy_window() -> None:
    """Shut pygame down (C: free + SDL_Destroy* + SDL_Quit)."""
    pygame.quit()


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

        clock.tick(FPS)  # CONVENTIONS.md §7 frame cap (C step 7 has none)

        # --- Test hooks (CONVENTIONS.md §7) ---
        frame_count += 1
        if max_frames is not None and frame_count >= max_frames:
            is_running = False
        # --------------------------------------

    # --- Test hooks (CONVENTIONS.md §7): save the last presented frame. ---
    if save_frame_path and window is not None:
        pygame.image.save(window, save_frame_path)
    # -----------------------------------------------------------------------

    destroy_window()


if __name__ == "__main__":
    main()
