"""camera.py — mirrors src/camera.c and src/camera.h.

Owns the single global camera: position, viewing direction, forward
velocity, and yaw angle. From step 48 the KEYBOARD drives it — main.c
translates key presses into position/yaw changes scaled by delta_time, and
the look-at target is rebuilt from the yaw every frame.

In C this is a global ``camera_t camera`` initialized to position (0,0,0)
and direction (0,0,1); the module-level instance below mirrors that.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from vector import Vec3


@dataclass
class camera_t:
    """The scene camera state, as in camera.h (velocity + yaw new in step 48)."""

    position: Vec3 = field(default_factory=lambda: np.array([0.0, 0.0, 0.0]))
    direction: Vec3 = field(default_factory=lambda: np.array([0.0, 0.0, 1.0]))
    forward_velocity: Vec3 = field(default_factory=lambda: np.array([0.0, 0.0, 0.0]))
    yaw: float = 0.0  # rotation around the y axis, driven by the a/d keys


# Global camera — mirrors `camera_t camera = { .position = {0,0,0},
# .direction = {0,0,1} };` in camera.c.
camera = camera_t()
