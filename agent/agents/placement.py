"""Deterministic placement of objects within a declared zone.

V1 places at zone y-midpoint and spreads x/z by index. Real spatial planning
(collision avoidance, scale-aware spacing) is v2.
"""

from __future__ import annotations

GRID_COLS = 5
GRID_SPACING = 0.3


def place_in_zone(
    zone: str,
    zone_map: dict[str, dict[str, list[float]]],
    index: int = 0,
) -> tuple[float, float, float]:
    if zone not in zone_map:
        raise ValueError(f"unknown zone: {zone!r}")
    y_range = zone_map[zone]["yRange"]
    y = (y_range[0] + y_range[1]) / 2.0
    col = index % GRID_COLS
    row = index // GRID_COLS
    x = (col - GRID_COLS // 2) * GRID_SPACING
    z = row * GRID_SPACING
    return (float(x), float(y), float(z))
