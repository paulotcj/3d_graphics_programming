"""camera.py — mirrors src/camera.c.

Owns the single global FPS-style camera: position, viewing direction,
forward velocity, and yaw angle. At this step camera.c holds only the
struct and its initial values — all camera math (look-at target, yaw
rotation, forward movement) still lives in main.py, exactly like main.c.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from vector import Vec3, vec3_new


@dataclass
class camera_t:
    """The scene camera state (see module docstring)."""

    position: Vec3 = field(default_factory=lambda: vec3_new(0, 0, 0))
    direction: Vec3 = field(default_factory=lambda: vec3_new(0, 0, 1))
    forward_velocity: Vec3 = field(default_factory=lambda: vec3_new(0, 0, 0))
    yaw: float = 0.0


# Module-level state — mirrors the `camera_t camera` global in camera.c,
# initialized with the same values as the C designated initializer.
camera = camera_t()
