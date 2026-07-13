"""texture.py — mirrors src/texture.c (+ replaces upng.c/upng.h).

Owns the ``tex2_t`` UV-coordinate type from texture.h and the global mesh
texture that mirrors texture.c's translation-unit globals:

    C                        Python
    ---------------------    ---------------------------------------------
    int texture_width        texture_width (module global)
    int texture_height       texture_height (module global)
    uint32_t* mesh_texture   mesh_texture — NumPy uint32 (height, width)
    upng_t* png_texture      (not needed — pygame decodes the PNG)

The C project decodes PNGs with the bundled uPNG library (1,281 lines);
here one ``pygame.image.load`` call does the same job (CONVENTIONS.md §2).

Texel format: the C code cast the raw PNG byte buffer to ``uint32_t*`` and
indexed it as ``texels[texture_width * y + x]``. Here ``mesh_texture`` is a
NumPy ``uint32`` array of shape ``(height, width)`` holding ``0xAARRGGBB``
values — the same pixel convention as the color buffer (CONVENTIONS.md §4) —
so a fancy-indexed fetch ``mesh_texture[tex_y, tex_x]`` can be stored
straight into the color buffer with no per-pixel conversion.
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


# Module-level state — mirrors the globals at the top of texture.c.
texture_width: int = 64
texture_height: int = 64
mesh_texture: np.ndarray | None = None  # (height, width) uint32, 0xAARRGGBB


def load_png_texture_data(filename: str) -> None:
    """Load a PNG into the global mesh texture (C: uPNG decode + globals).

    On failure the globals are left untouched, mirroring how the C code
    only assigns them when uPNG reports UPNG_EOK.
    """
    global texture_width, texture_height, mesh_texture

    try:
        surface = pygame.image.load(filename)
    except (pygame.error, FileNotFoundError):
        print(f"Warning: could not load texture '{filename}'.")
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
    # width) to match the C row-major indexing texels[texture_width * y + x].
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


def tex2_clone(t: tex2_t) -> tex2_t:
    """Return a copy of a texture coordinate (C: tex2_clone, new in step 54)."""
    return tex2_t(u=t.u, v=t.v)
