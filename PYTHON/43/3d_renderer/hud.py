"""hud.py — on-screen keyboard help, identical in every step of this course.

Every step of the renderer reacts to some keys (at minimum ESC). This tiny
module keeps that discoverable:

- a small "H — controls" hint sits in the bottom-left corner at all times;
- pressing **H** toggles a panel listing every key the CURRENT step handles
  and what it does (the list is passed in by main.py, so it always matches
  the real handlers).

The HUD draws straight onto the pygame window AFTER the 3D frame is blitted
and BEFORE the flip, so it never touches the color buffer — the software
renderer stays byte-identical with the C original; only the presented window
gains the overlay.
"""

from __future__ import annotations

import pygame

# One entry per key: (key label, what it does). Filled by init_hud().
_bindings: list[tuple[str, str]] = []
_visible: bool = False

_font: pygame.font.Font | None = None
_small_font: pygame.font.Font | None = None

_HINT_TEXT = "H — controls"
_PANEL_BG = (12, 12, 16, 215)   # dark, mostly opaque
_KEY_COLOR = (255, 210, 90)     # warm yellow for the key names
_TEXT_COLOR = (230, 230, 230)
_HINT_COLOR = (160, 160, 160)


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


def draw(window: pygame.Surface) -> None:
    """Draw the hint (always) or the full bindings panel (when toggled on).

    Call right before pygame.display.flip(), after the frame is blitted.
    """
    _ensure_fonts()
    assert _font is not None and _small_font is not None

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
