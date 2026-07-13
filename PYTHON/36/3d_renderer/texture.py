"""texture.py — mirrors src/texture.c / src/texture.h of C step 36.

Owns the texture state: the ``tex2_t`` UV-coordinate type, the texture
dimensions, and the global ``mesh_texture`` the rasterizer samples from.

**Substitution note (CONVENTIONS.md §2):** the C file embeds the 64x64
red-brick texture as a 16,384-byte ``REDBRICK_TEXTURE[]`` array pasted into
the source. Those exact bytes were exported once to ``assets/redbrick.png``
(pixel-identical), and this module loads them back at startup — same texels,
sane storage. The C line

    mesh_texture = (uint32_t*) REDBRICK_TEXTURE;

becomes ``texture.mesh_texture = load_redbrick_texture()`` in main.py.

The texture is a NumPy ``uint32`` array of shape (height, width) holding
``0xAARRGGBB`` values — identical in layout to the color buffer, so a texel
can be stored into the framebuffer with no conversion.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np
import pygame

texture_width: int = 64
texture_height: int = 64

# The global texture the renderer samples (C: uint32_t* mesh_texture).
# Assigned by main.setup(), exactly where the C assigns it.
mesh_texture: np.ndarray | None = None


@dataclass
class tex2_t:
    """A texture coordinate pair: u (horizontal), v (vertical), both 0..1."""

    u: float = 0.0
    v: float = 0.0


def load_redbrick_texture() -> np.ndarray:
    """Load assets/redbrick.png into a (height, width) uint32 ARGB array.

    pygame decodes the PNG; ``tobytes(..., "BGRA")`` emits the byte order
    that a little-endian uint32 reads back as 0xAARRGGBB — the exact values
    the C code had in its REDBRICK_TEXTURE array.
    """
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "redbrick.png")
    surface = pygame.image.load(path)
    raw = pygame.image.tobytes(surface, "BGRA")
    return np.frombuffer(raw, dtype=np.uint32).reshape(surface.get_height(), surface.get_width()).copy()
