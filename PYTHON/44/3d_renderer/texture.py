"""texture.py — mirrors src/texture.c and texture.h of C step 41.

Owns the ``tex2_t`` UV-coordinate type, the texture size globals, and the
``mesh_texture`` the rasterizer samples.

Step 41 in C replaces the hard-coded REDBRICK_TEXTURE array with **PNG
loading** via the bundled uPNG decoder (upng.c, 1,281 lines) and switches
the SDL window texture to ``SDL_PIXELFORMAT_RGBA32`` so the decoded bytes
display correctly.

The Python conversion collapses all of that into one ``pygame.image.load``
call (CONVENTIONS.md §2): pygame decodes the PNG and ``tobytes(.., "BGRA")``
emits exactly the byte order a little-endian uint32 reads back as
``0xAARRGGBB`` — the same ARGB convention the color buffer has used since
step 3. Because the *loader* already lands in our buffer's format, the C's
window-format switch needs no mirror: the on-screen result is identical.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np
import pygame


@dataclass
class tex2_t:
    """A single UV texture coordinate."""

    u: float
    v: float


# Module-level state — mirrors the globals in texture.c.
texture_width: int = 64
texture_height: int = 64

# C: `uint32_t* mesh_texture = NULL;` — filled by load_png_texture_data().
mesh_texture: np.ndarray | None = None


def load_png_texture_data(filename: str) -> None:
    """Load a PNG file into mesh_texture and update the texture dimensions.

    Mirrors load_png_texture_data() in texture.c, where uPNG decodes the
    file into an RGBA byte buffer (`png_texture`, freed later by
    upng_free). pygame does the decode here; there is nothing to free —
    Python's garbage collector owns the array.
    """
    global mesh_texture, texture_width, texture_height

    surface = pygame.image.load(filename)
    texture_width = surface.get_width()
    texture_height = surface.get_height()
    raw = pygame.image.tobytes(surface, "BGRA")
    mesh_texture = (
        np.frombuffer(raw, dtype=np.uint32).reshape(texture_height, texture_width).copy()
    )
