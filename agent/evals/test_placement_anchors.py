"""Anchor-based placement + size estimation + Placer composition tests.

Covers the spatial-composition fix: a "make a flower" brief produces
parts that line up correctly instead of scattering across the grid.
"""

from __future__ import annotations

import math

import pytest

from agent.agents.placement import (
    Placer,
    estimate_size,
    place_in_zone,
    resolve_anchor,
)
from agent.agents.types import AnchorSpec, ObjectSummaryItem
from agent.store.scene_store import ZONE_MAP


def _items(*specs):
    """Compact constructor: _items(("stem","lower"), ("petals","upper","stem","above"))."""
    out = []
    for spec in specs:
        if len(spec) == 2:
            label, zone = spec
            out.append(ObjectSummaryItem(label=label, zone=zone, stage="bloom"))
        else:
            label, zone, anchor_label, placement = spec
            out.append(
                ObjectSummaryItem(
                    label=label,
                    zone=zone,
                    stage="bloom",
                    anchor=AnchorSpec(relativeTo=anchor_label, placement=placement),
                )
            )
    return out


def test_estimate_size_box() -> None:
    assert estimate_size("BoxGeometry", [0.5, 1.0, 0.5]) == (0.5, 1.0, 0.5)


def test_estimate_size_sphere() -> None:
    # Sphere bbox = (2r, 2r, 2r)
    assert estimate_size("SphereGeometry", [0.2, 16, 16]) == (0.4, 0.4, 0.4)


def test_estimate_size_cylinder() -> None:
    # Cylinder bbox = (2*max(rt,rb), height, 2*max(rt,rb))
    assert estimate_size("CylinderGeometry", [0.05, 0.08, 0.6, 8]) == (0.16, 0.6, 0.16)


def test_estimate_size_torus() -> None:
    # Torus bbox: 2(r+t) on x/z, 2t on y.
    w, h, d = estimate_size("TorusGeometry", [0.3, 0.05])
    assert math.isclose(w, 0.7)
    assert math.isclose(h, 0.1)
    assert math.isclose(d, 0.7)


def test_estimate_size_unknown_falls_back_to_unit() -> None:
    assert estimate_size("MysteryGeometry", [1, 2, 3]) == (1.0, 1.0, 1.0)


def test_resolve_anchor_above_clears_both_bounds() -> None:
    """Child sits its bottom on parent's top (+ offset). Distance =
    parent_h/2 + child_h/2 + offset along y."""
    parent = (0.0, 0.5, 0.0)
    parent_size = (0.2, 0.6, 0.2)  # 0.6 tall, top at y=0.8
    child_size = (0.4, 0.1, 0.4)  # 0.1 tall, center should land at 0.8 + 0.05 = 0.85
    anchor = AnchorSpec(relativeTo="parent", placement="above")
    pos = resolve_anchor(parent, parent_size, child_size, anchor)
    assert pos[1] == pytest.approx(0.85)
    assert pos[0] == 0.0
    assert pos[2] == 0.0


def test_resolve_anchor_left_right_x_offset() -> None:
    parent = (0.0, 0.3, 0.0)
    parent_size = (0.1, 0.6, 0.1)
    child_size = (0.2, 0.1, 0.2)
    left = resolve_anchor(parent, parent_size, child_size, AnchorSpec(relativeTo="x", placement="left"))
    right = resolve_anchor(parent, parent_size, child_size, AnchorSpec(relativeTo="x", placement="right"))
    # parent half-width 0.05 + child half-width 0.1 = 0.15 from parent center
    assert left[0] == pytest.approx(-0.15)
    assert right[0] == pytest.approx(0.15)


def test_resolve_anchor_offset_adds_extra_clearance() -> None:
    parent = (0.0, 0.0, 0.0)
    psize = (0.0, 0.0, 0.0)
    csize = (0.0, 0.0, 0.0)
    pos = resolve_anchor(parent, psize, csize, AnchorSpec(relativeTo="x", placement="above", offset=0.5))
    assert pos[1] == pytest.approx(0.5)


def test_placer_root_centered() -> None:
    """A no-anchor item that's referenced by other items goes to the zone
    center (x=0, z=0), not the index-based grid spot."""
    items = _items(
        ("stem", "lower"),
        ("petals", "upper", "stem", "above"),
    )
    placer = Placer(items, ZONE_MAP)
    stem_pos = placer.place(0, items[0], "CylinderGeometry", [0.05, 0.08, 0.6, 8])
    assert stem_pos[0] == 0.0
    assert stem_pos[2] == 0.0


def test_placer_anchor_resolves_against_root() -> None:
    """Petals anchored 'above' the stem should land at x=z=0 (centered)
    above the stem's top."""
    items = _items(
        ("stem", "lower"),
        ("petals", "upper", "stem", "above"),
    )
    placer = Placer(items, ZONE_MAP)
    placer.place(0, items[0], "CylinderGeometry", [0.05, 0.08, 0.6, 8])
    petals_pos = placer.place(1, items[1], "TorusGeometry", [0.18, 0.05])
    assert petals_pos[0] == pytest.approx(0.0)
    assert petals_pos[2] == pytest.approx(0.0)
    # stem center y=0.3, height 0.6 -> top at 0.6. Petals tube y-extent = 0.1,
    # so petals center y = 0.6 + 0.05 = 0.65.
    assert petals_pos[1] == pytest.approx(0.65)


def test_placer_left_right_leaves_align_with_stem() -> None:
    items = _items(
        ("stem", "lower"),
        ("leaf_left", "lower", "stem", "left"),
        ("leaf_right", "lower", "stem", "right"),
    )
    placer = Placer(items, ZONE_MAP)
    placer.place(0, items[0], "CylinderGeometry", [0.05, 0.08, 0.6, 8])
    left = placer.place(1, items[1], "PlaneGeometry", [0.2, 0.12])
    right = placer.place(2, items[2], "PlaneGeometry", [0.2, 0.12])
    assert left[0] < 0
    assert right[0] > 0
    # Same y-band (lower zone center)
    assert left[1] == pytest.approx(right[1])


def test_placer_unresolvable_anchor_falls_back_to_grid() -> None:
    """If `relativeTo` references a label not yet placed (or never in the
    brief), the item falls through to grid placement."""
    items = _items(
        ("a", "lower", "ghost", "above"),  # 'ghost' is never declared
    )
    placer = Placer(items, ZONE_MAP)
    pos = placer.place(0, items[0], "BoxGeometry", [1, 1, 1])
    # Grid placement at index=0 -> col=0, x = (0-2)*0.3 = -0.6
    assert pos[0] == pytest.approx(-0.6)


def test_placer_stacking_heuristic_for_small_anchor_free_brief() -> None:
    """A <= 6-item brief with NO anchors at all stacks at x=z=0 by zone."""
    items = _items(
        ("a", "ground"),
        ("b", "lower"),
        ("c", "mid"),
    )
    placer = Placer(items, ZONE_MAP)
    positions = [
        placer.place(i, item, "BoxGeometry", [0.1, 0.1, 0.1])
        for i, item in enumerate(items)
    ]
    for pos in positions:
        assert pos[0] == 0.0
        assert pos[2] == 0.0


def test_placer_grid_for_large_anchor_free_brief() -> None:
    """7+ items with no anchors fall back to grid (current M5 behavior)."""
    items = [
        ObjectSummaryItem(label=f"obj_{i}", zone="lower", stage="x") for i in range(7)
    ]
    placer = Placer(items, ZONE_MAP)
    positions = [
        placer.place(i, item, "BoxGeometry", [0.1, 0.1, 0.1])
        for i, item in enumerate(items)
    ]
    # First three should NOT all be at x=0 (proves stacking didn't kick in).
    xs = {p[0] for p in positions[:3]}
    assert len(xs) > 1


def test_place_in_zone_back_compat() -> None:
    """The original M5 helper is still exposed for tests / fallback."""
    pos = place_in_zone("lower", ZONE_MAP, index=0)
    assert pos[1] == pytest.approx(0.3)
