"""camera.py — mirrors src/camera.c and src/camera.h.

Owns the single global camera introduced in this step: a position and a
viewing direction. main.c nudges ``camera.position`` every frame and feeds
it to ``mat4_look_at`` to build the view matrix, so the whole scene is now
expressed in camera space before projection.

In C this is a global ``camera_t camera`` initialized to position (0,0,0)
and direction (0,0,1); the module-level instance below mirrors that.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from vector import Vec3


@dataclass
class camera_t:
    """The scene camera state (position + facing direction), as in camera.h."""

    position: Vec3 = field(default_factory=lambda: np.array([0.0, 0.0, 0.0]))
    direction: Vec3 = field(default_factory=lambda: np.array([0.0, 0.0, 1.0]))


# Global camera — mirrors `camera_t camera = { .position = {0,0,0},
# .direction = {0,0,1} };` in camera.c.
camera = camera_t()
