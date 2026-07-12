"""texture.py — mirrors src/texture.c and texture.h.

Owns the ``tex2_t`` UV-coordinate type, the texture size globals, the
``mesh_texture`` pointer, and the hard-coded 64x64 red-brick texture.

In the C file ``REDBRICK_TEXTURE`` is a ``const uint8_t[16384]`` literal
(64 x 64 texels, 4 bytes each) that main.c casts to ``uint32_t*``. On a
little-endian machine the byte quadruple ``0x38 0x38 0x38 0xff`` reads back
as the uint32 ``0xFF383838`` — i.e. the same 0xAARRGGBB convention as the
color buffer (CONVENTIONS.md §4). Rather than paste 16 KB of hex literals
into this module, the exact same bytes are stored zlib-compressed +
base64-encoded and decoded at import time into a ``(64, 64)`` uint32 NumPy
array, so ``texture[tex_y, tex_x]`` matches the C indexing
``texture[texture_width * tex_y + tex_x]`` one for one.
"""

from __future__ import annotations

import base64
import zlib
from dataclasses import dataclass

import numpy as np


@dataclass
class tex2_t:
    """A single UV texture coordinate."""

    u: float
    v: float


# Module-level state — mirrors the globals in texture.c.
texture_width: int = 64
texture_height: int = 64

# C: `uint32_t* mesh_texture = NULL;` — main.py points this at
# REDBRICK_TEXTURE during setup().
mesh_texture: np.ndarray | None = None

# The C REDBRICK_TEXTURE byte array (16,384 bytes), zlib + base64 encoded.
# Decoding it and viewing the bytes as little-endian uint32 reproduces the
# exact texel values the C code reads through its uint32_t* cast.
_REDBRICK_TEXTURE_DATA = (
    "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"
)

# Decode once at import: bytes -> little-endian uint32 view -> (64, 64) grid.
REDBRICK_TEXTURE: np.ndarray = (
    np.frombuffer(zlib.decompress(base64.b64decode(_REDBRICK_TEXTURE_DATA)), dtype="<u4")
    .reshape(texture_height, texture_width)
    .copy()
)
