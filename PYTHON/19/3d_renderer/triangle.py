"""triangle.py — mirrors src/triangle.c / src/triangle.h of C step 18.

Two tiny data types that turn loose points into *geometry*:

    face_t     — three 1-based indexes (a, b, c) into the mesh vertex list;
                 a face stores *which* vertices form a triangle, not where
                 they are.
    triangle_t — the three projected 2D screen points of one face, ready to
                 be drawn.

(triangle.c itself is empty at this step — rasterization functions arrive
later.)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from vector import Vec2


@dataclass
class face_t:
    """Indexes (1-based, exactly as in the C and in .obj files) of a triangle's vertices."""

    a: int
    b: int
    c: int


@dataclass
class triangle_t:
    """The three projected screen-space points of one mesh face."""

    points: list[Vec2] = field(
        default_factory=lambda: [np.zeros(2, dtype=np.float64) for _ in range(3)]
    )
