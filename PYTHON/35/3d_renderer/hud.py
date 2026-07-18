"""hud.py — on-screen overlays, identical in every step of this course.

Two small overlays are drawn straight onto the pygame window AFTER the 3D
frame is blitted and BEFORE the flip, so they never touch the color buffer —
the software renderer stays byte-identical with the C original; only the
presented window gains the overlay.

- **FPS counter** in the top-right corner (e.g. ``FPS : 60``), measured from
  the real wall-clock time between frames so it reflects the actually
  displayed rate.
- **Key help**: a small "H — controls" hint in the bottom-left corner, and a
  panel (toggled with **H**) listing every key the CURRENT step handles and
  what it does (the list is passed in by main.py, so it always matches the
  real handlers).
"""

from __future__ import annotations

import pygame

# --- key-help state ---------------------------------------------------------
# One entry per key: (key label, what it does). Filled by init_hud().
_bindings: list[tuple[str, str]] = []
_visible: bool = False

# --- FPS-counter state ------------------------------------------------------
_last_tick_ms: int | None = None   # timestamp of the previous frame
_fps_ema: float = 0.0              # smoothed frames-per-second estimate
_FPS_SMOOTHING = 0.9              # weight kept from the previous estimate

_font: pygame.font.Font | None = None
_small_font: pygame.font.Font | None = None

_HINT_TEXT = "H — controls"
_PANEL_BG = (12, 12, 16, 215)   # dark, mostly opaque
_KEY_COLOR = (255, 210, 90)     # warm yellow for the key names
_TEXT_COLOR = (230, 230, 230)
_HINT_COLOR = (160, 160, 160)
_FPS_COLOR = (120, 230, 120)    # green


def init_hud(bindings: list[tuple[str, str]]) -> None:
    """Register this step's key bindings (call once, before the game loop)."""
    global _bindings
    _bindings = [("H", "show / hide this help")] + list(bindings)


def handle_event(event: pygame.event.Event) -> None:
    """Toggle the help panel on H. Call for every event in process_input."""
    global _visible
    if event.type == pygame.KEYDOWN and event.key == pygame.K_h:
        _visible = not _visible


def _ensure_fonts() -> None:
    global _font, _small_font
    if _font is None:
        if not pygame.font.get_init():
            pygame.font.init()
        _font = pygame.font.Font(None, 22)
        _small_font = pygame.font.Font(None, 18)


def _update_fps() -> None:
    """Fold this frame's duration into the smoothed FPS estimate.

    dt is the wall-clock gap since the previous draw() call — one full frame
    period — so 1000/dt is the instantaneous FPS. An exponential moving
    average keeps the on-screen number steady instead of flickering.
    """
    global _last_tick_ms, _fps_ema
    now = pygame.time.get_ticks()
    if _last_tick_ms is not None:
        dt = now - _last_tick_ms
        if dt > 0:
            instantaneous = 1000.0 / dt
            _fps_ema = (
                instantaneous
                if _fps_ema == 0.0
                else _FPS_SMOOTHING * _fps_ema + (1.0 - _FPS_SMOOTHING) * instantaneous
            )
    _last_tick_ms = now


def _draw_fps(window: pygame.Surface) -> None:
    """Render ``FPS : <n>`` in the top-right corner."""
    assert _small_font is not None
    text = f"FPS : {int(round(_fps_ema))}"
    surf = _small_font.render(text, True, _FPS_COLOR)
    window.blit(surf, (window.get_width() - surf.get_width() - 8, 6))


def draw(window: pygame.Surface) -> None:
    """Draw the FPS counter and the key-help overlay.

    Call right before pygame.display.flip(), after the frame is blitted.
    """
    _ensure_fonts()
    assert _font is not None and _small_font is not None

    _update_fps()
    _draw_fps(window)

    if not _visible:
        hint = _small_font.render(_HINT_TEXT, True, _HINT_COLOR)
        window.blit(hint, (8, window.get_height() - hint.get_height() - 6))
        return

    line_height = _font.get_height() + 6
    key_column = max((_font.size(key)[0] for key, _ in _bindings), default=20) + 18
    panel_width = key_column + max(
        (_font.size(action)[0] for _, action in _bindings), default=100
    ) + 28
    panel_height = line_height * len(_bindings) + 20

    panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
    panel.fill(_PANEL_BG)

    y = 10
    for key, action in _bindings:
        panel.blit(_font.render(key, True, _KEY_COLOR), (14, y))
        panel.blit(_font.render(action, True, _TEXT_COLOR), (key_column, y))
        y += line_height

    window.blit(panel, (10, 10))
