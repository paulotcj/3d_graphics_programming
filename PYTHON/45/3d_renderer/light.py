"""light.py — mirrors src/light.c.

Owns the single global directional light and the flat-shading intensity
helper. Flat shading: each triangle gets ONE brightness for its whole
surface, computed in main.py as ``-dot(face_normal, light_direction)``.
The negation is there because a face whose normal points *against* the
incoming light rays (dot product negative) is the face that is lit.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from vector import Vec3


@dataclass
class light_t:
    """A directional light — only a direction, no position or falloff."""

    direction: Vec3 = field(default_factory=lambda: np.array([0.0, 0.0, 1.0]))


# Module-level state — mirrors the global `light_t light` in light.c.
light = light_t(direction=np.array([0.0, 0.0, 1.0], dtype=np.float64))


###############################################################################
# Change color based on a percentage factor to represent light intensity
###############################################################################
def light_apply_intensity(original_color: int, percentage_factor: float) -> int:
    """Scale the RGB channels of a 0xAARRGGBB color by a factor (clamped 0..1).

    Mirrors the C bit-mask trick exactly: each channel is scaled while still
    sitting at its position inside the uint32, then re-masked to throw away
    any bits that spilled into the neighboring channel.
    """
    if percentage_factor < 0:
        percentage_factor = 0
    if percentage_factor > 1:
        percentage_factor = 1

    a = original_color & 0xFF000000
    r = int((original_color & 0x00FF0000) * percentage_factor)
    g = int((original_color & 0x0000FF00) * percentage_factor)
    b = int((original_color & 0x000000FF) * percentage_factor)

    new_color = a | (r & 0x00FF0000) | (g & 0x0000FF00) | (b & 0x000000FF)

    return new_color
