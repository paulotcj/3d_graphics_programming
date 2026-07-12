"""texture.py — mirrors src/texture.c (+ replaces upng.c/upng.h).

Owns the ``tex2_t`` UV-coordinate type from texture.h, plus the global mesh
texture that texture.c exposes as ``mesh_texture`` / ``texture_width`` /
``texture_height``. The C project decodes PNGs with its bundled uPNG decoder
(1,281 lines of C); here that entire job is one ``pygame.image.load`` call
(CONVENTIONS.md §2).

Texel format: the C code cast the raw PNG byte buffer to ``uint32_t*`` and
indexed it as ``texture[texture_width * y + x]``. Here ``mesh_texture`` is a
NumPy ``uint32`` array of shape ``(height, width)`` holding ``0xAARRGGBB``
values — the same pixel convention as the color buffer (CONVENTIONS.md §4) —
so a fancy-indexed fetch ``mesh_texture[tex_y, tex_x]`` can be stored straight
into the color buffer with no per-pixel conversion.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np
import pygame

# Directory of this file — the §8 fallback cube.png is resolved against it,
# never against the current working directory (CONVENTIONS.md §7).
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


@dataclass
class tex2_t:
    """A single UV texture coordinate (u across, v up — v is flipped at raster time)."""

    u: float
    v: float


# Module-level state — mirrors the globals at the top of texture.c.
texture_width: int = 64
texture_height: int = 64
mesh_texture: np.ndarray | None = None  # (height, width) uint32, 0xAARRGGBB


def load_png_texture_data(filename: str) -> None:
    """Load a PNG into the global mesh texture.

    Replaces upng_new_from_file + upng_decode + upng_get_buffer. On failure
    the C code kept ``mesh_texture`` NULL; here a one-line warning is printed
    and ``assets/cube.png`` is tried as a fallback (CONVENTIONS.md §8) so
    textured mode still shows something. If even that fails, the globals are
    left untouched and textured mode draws nothing.
    """
    global texture_width, texture_height, mesh_texture

    try:
        surface = pygame.image.load(filename)
    except (pygame.error, FileNotFoundError):
        print(f"Warning: could not load texture {filename} — falling back to cube.png.")
        try:
            surface = pygame.image.load(os.path.join(_MODULE_DIR, "assets", "cube.png"))
        except (pygame.error, FileNotFoundError):
            print("Warning: cube.png fallback also missing — textured mode will draw nothing.")
            return

    # Normalize to a 32-bit surface with per-pixel alpha so the channel
    # extraction below always sees the same layout. convert_alpha() needs an
    # open window; if there is none, fall back to the raw surface —
    # array3d/array_alpha still work.
    try:
        surface = surface.convert_alpha()
    except pygame.error:
        pass

    # pygame's surfarray views are (width, height); transpose to (height,
    # width) to match the C row-major indexing texture[texture_width * y + x].
    rgb = pygame.surfarray.array3d(surface).astype(np.uint32)  # (w, h, 3)
    try:
        alpha = pygame.surfarray.array_alpha(surface).astype(np.uint32)  # (w, h)
    except (pygame.error, ValueError):
        alpha = np.full(rgb.shape[:2], 255, dtype=np.uint32)

    # Pack the channels into 0xAARRGGBB uint32 values (CONVENTIONS.md §4).
    argb = (alpha << 24) | (rgb[..., 0] << 16) | (rgb[..., 1] << 8) | rgb[..., 2]

    mesh_texture = np.ascontiguousarray(argb.T)  # (height, width)
    texture_width = surface.get_width()
    texture_height = surface.get_height()
