"""camera.py — mirrors src/camera.c.

Owns the single global FPS-style camera: position, viewing direction,
forward velocity, and yaw/pitch angles. The camera in this step never rolls;
its look-at target is rebuilt every frame from yaw + pitch in
``get_camera_lookat_target``.

Note: like the C program (which never calls ``init_camera`` and relies on
static zero-initialization), the camera starts at the origin looking down
the positive z-axis.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from matrix import (
    mat4_identity,
    mat4_make_rotation_x,
    mat4_make_rotation_y,
    mat4_mul_mat4,
    mat4_mul_vec4,
)
from vector import Vec3, vec3_add, vec3_from_vec4, vec3_new, vec4_from_vec3


@dataclass
class camera_t:
    """The scene camera state (see module docstring)."""

    position: Vec3 = field(default_factory=lambda: vec3_new(0, 0, 0))
    direction: Vec3 = field(default_factory=lambda: vec3_new(0, 0, 0))
    forward_velocity: Vec3 = field(default_factory=lambda: vec3_new(0, 0, 0))
    yaw: float = 0.0
    pitch: float = 0.0


# Module-level state — mirrors the `static camera_t camera` in camera.c,
# zero-initialized exactly like the C static.
_camera = camera_t()


def init_camera(position: Vec3, direction: Vec3) -> None:
    """Reset the camera to a given position and direction."""
    _camera.position = position
    _camera.direction = direction
    _camera.forward_velocity = vec3_new(0, 0, 0)
    _camera.yaw = 0.0
    _camera.pitch = 0.0


def get_camera_position() -> Vec3:
    """Return the camera position in world space."""
    return _camera.position


def get_camera_direction() -> Vec3:
    """Return the direction the camera is currently facing."""
    return _camera.direction


def get_camera_forward_velocity() -> Vec3:
    """Return the velocity applied when moving forward/backward."""
    return _camera.forward_velocity


def get_camera_yaw() -> float:
    """Return the yaw angle (rotation around the y-axis) in radians."""
    return _camera.yaw


def get_camera_pitch() -> float:
    """Return the pitch angle (rotation around the x-axis) in radians."""
    return _camera.pitch


def update_camera_position(position: Vec3) -> None:
    """Replace the camera position."""
    _camera.position = position


def update_camera_direction(direction: Vec3) -> None:
    """Replace the camera facing direction."""
    _camera.direction = direction


def update_camera_forward_velocity(forward_velocity: Vec3) -> None:
    """Replace the forward velocity vector."""
    _camera.forward_velocity = forward_velocity


def rotate_camera_yaw(angle: float) -> None:
    """Add to the yaw angle (left/right arrow keys)."""
    _camera.yaw += angle


def rotate_camera_pitch(angle: float) -> None:
    """Add to the pitch angle (w/s keys)."""
    _camera.pitch += angle


def get_camera_lookat_target() -> Vec3:
    """Compute the point the camera is looking at from its yaw and pitch.

    Starts from a canonical target straight down the +z axis, rotates it by
    pitch (around x) then yaw (around y), stores the resulting direction,
    and returns position + direction — the target for mat4_look_at.
    """
    # Initialize the target looking at the positive z-axis
    target = vec3_new(0, 0, 1)

    camera_yaw_rotation = mat4_make_rotation_y(_camera.yaw)
    camera_pitch_rotation = mat4_make_rotation_x(_camera.pitch)

    # Create camera rotation matrix based on yaw and pitch
    camera_rotation = mat4_identity()
    camera_rotation = mat4_mul_mat4(camera_pitch_rotation, camera_rotation)
    camera_rotation = mat4_mul_mat4(camera_yaw_rotation, camera_rotation)

    # Update camera direction based on the rotation
    camera_direction = mat4_mul_vec4(camera_rotation, vec4_from_vec3(target))
    _camera.direction = vec3_from_vec4(camera_direction)

    # Offset the camera position in the direction where the camera is pointing at
    target = vec3_add(_camera.position, _camera.direction)
    return target
