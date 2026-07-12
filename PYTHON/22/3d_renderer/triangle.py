"""triangle.py — mirrors src/triangle.h (triangle.c is empty at this step).

Owns the two plain data types the pipeline moves around:

- ``face_t``      — one triangle of the mesh, as three **1-based** indexes
                    into the mesh vertex list (exactly like the C struct and
                    like the OBJ format that arrives in the next step).
- ``triangle_t``  — one triangle after projection: three 2D screen points.

The C ``triangle.c`` at step 21 contains only a TODO comment; the drawing
functions still live in display.c / display.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from vector import Vec2, vec2_new


@dataclass
class face_t:
    """Three 1-based vertex indexes describing one mesh triangle."""

    a: int
    b: int
    c: int


@dataclass
class triangle_t:
    """Three projected 2D screen-space points of a triangle."""

    points: list[Vec2] = field(
        default_factory=lambda: [vec2_new(0, 0), vec2_new(0, 0), vec2_new(0, 0)]
    )
