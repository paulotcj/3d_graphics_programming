"""texture.py — mirrors src/texture.c (+ replaces upng.c/upng.h).

Owns the ``tex2_t`` UV-coordinate type from texture.c, plus the texture
image type that replaces the C project's uPNG decoder (1,281 lines of C
become one ``pygame.image.load`` call, see CONVENTIONS.md §2).

Texel format: the C code cast the raw PNG byte buffer to ``uint32_t*`` and
indexed it as ``texels[width * y + x]``. Here ``texture_t.texels`` is a NumPy
``uint32`` array of shape ``(height, width)`` holding ``0xAARRGGBB`` values —
the same pixel convention as the color buffer (CONVENTIONS.md §4) — so a
fancy-indexed fetch ``texels[tex_y, tex_x]`` can be stored straight into the
color buffer with no per-pixel conversion.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pygame


@dataclass
class tex2_t:
    """A single UV texture coordinate (u across, v up — v is flipped at raster time)."""

    u: float
    v: float


def tex2_clone(t: tex2_t) -> tex2_t:
    """Return an independent copy of a texture coordinate (mirrors tex2_clone)."""
    return tex2_t(t.u, t.v)


@dataclass
class texture_t:
    """A decoded texture image — the Python replacement for the C ``upng_t``.

    Attributes:
        width:  texture width in pixels  (mirrors upng_get_width).
        height: texture height in pixels (mirrors upng_get_height).
        texels: ``(height, width)`` uint32 array of 0xAARRGGBB colors
                (mirrors upng_get_buffer cast to ``uint32_t*``).
    """

    width: int
    height: int
    texels: np.ndarray


def load_png_texture(png_filename: str) -> texture_t | None:
    """Load a PNG into a ``texture_t`` (replaces upng_new_from_file + upng_decode).

    Returns ``None`` if the file cannot be loaded, mirroring how the C code
    left ``mesh->texture`` untouched when uPNG reported an error.
    """
    try:
        surface = pygame.image.load(png_filename)
    except (pygame.error, FileNotFoundError):
        return None

    # Normalize to a 32-bit surface with per-pixel alpha so the channel
    # extraction below always sees the same layout. convert_alpha() needs an
    # open window; if there is none (e.g. unit tests) fall back to the raw
    # surface — array3d/array_alpha still work.
    try:
        surface = surface.convert_alpha()
    except pygame.error:
        pass

    # pygame's surfarray views are (width, height); transpose to (height,
    # width) to match the C row-major indexing texels[width * y + x].
    rgb = pygame.surfarray.array3d(surface).astype(np.uint32)  # (w, h, 3)
    try:
        alpha = pygame.surfarray.array_alpha(surface).astype(np.uint32)  # (w, h)
    except (pygame.error, ValueError):
        alpha = np.full(rgb.shape[:2], 255, dtype=np.uint32)

    # Pack the channels into 0xAARRGGBB uint32 values (CONVENTIONS.md §4).
    argb = (alpha << 24) | (rgb[..., 0] << 16) | (rgb[..., 1] << 8) | rgb[..., 2]
    texels = np.ascontiguousarray(argb.T)  # (height, width)

    return texture_t(width=surface.get_width(), height=surface.get_height(), texels=texels)
