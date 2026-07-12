"""light.py — mirrors src/light.c.

Owns the single global directional light and the flat-shading intensity
helper. Flat shading: each triangle gets ONE brightness for its whole
surface, computed in main.py as ``-dot(face_normal, light_direction)``.
The negation is there because a face whose normal points *against* the
incoming light rays (dot product negative) is the face that is lit.
"""

from __future__ import annotations

from dataclasses import dataclass

from vector import Vec3, vec3_new


@dataclass
class light_t:
    """A directional light — only a direction, no position or falloff."""

    direction: Vec3


# Module-level state — mirrors the `static light_t light` in light.c.
_light = light_t(direction=vec3_new(0, 0, 1))


def init_light(direction: Vec3) -> None:
    """Set the global scene light direction."""
    _light.direction = direction


def get_light_direction() -> Vec3:
    """Return the global scene light direction."""
    return _light.direction


def apply_light_intensity(original_color: int, factor: float) -> int:
    """Scale the RGB channels of a 0xAARRGGBB color by ``factor`` (clamped 0..1).

    Mirrors the C bit-mask trick exactly: each channel is scaled while still
    sitting at its position inside the uint32, then re-masked to throw away
    any bits that spilled into the neighboring channel.
    """
    if factor < 0:
        factor = 0
    if factor > 1:
        factor = 1

    a = original_color & 0xFF000000
    r = int((original_color & 0x00FF0000) * factor)
    g = int((original_color & 0x0000FF00) * factor)
    b = int((original_color & 0x000000FF) * factor)

    new_color = a | (r & 0x00FF0000) | (g & 0x0000FF00) | (b & 0x000000FF)

    return new_color
