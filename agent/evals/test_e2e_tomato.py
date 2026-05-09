"""End-to-end pipeline test against a real Anthropic LLM.

Gated by the `e2e` pytest marker; deselected by default. Run with:

    pytest -m e2e

Requires ANTHROPIC_API_KEY in .env (or environment). Each pipeline run costs a
handful of Anthropic API calls (1 director + N asset items). All three test
cases share a single session-scoped pipeline run so the cost stays predictable.
"""

from __future__ import annotations

import pytest

from agent.graph import run_pipeline
from agent.store.scene_store import SceneStore

VALID_GEOMETRY_TYPES = {
    "BoxGeometry",
    "SphereGeometry",
    "CylinderGeometry",
    "ConeGeometry",
    "PlaneGeometry",
    "TorusGeometry",
    "CircleGeometry",
}


@pytest.fixture(scope="session")
def tomato_events(real_llm):
    """One pipeline run shared across the e2e tests in this module."""
    store = SceneStore()
    return run_pipeline(
        "Walk me through a tomato plant's lifecycle",
        store,
        real_llm,
    )


@pytest.mark.e2e
def test_tomato_lifecycle_emits_minimum_events(tomato_events) -> None:
    counts: dict[str, int] = {}
    for event in tomato_events:
        counts[event.name] = counts.get(event.name, 0) + 1

    assert counts.get("scene:object_add", 0) >= 3, counts
    assert counts.get("scene:light_add", 0) >= 2, counts
    assert counts.get("scene:camera_move", 0) >= 1, counts


@pytest.mark.e2e
def test_tomato_lifecycle_all_objects_have_valid_geometry(tomato_events) -> None:
    object_events = [e for e in tomato_events if e.name == "scene:object_add"]
    assert object_events, "no object_add events emitted"
    for event in object_events:
        geometry = event.value["geometryType"]
        assert geometry in VALID_GEOMETRY_TYPES, (
            f"unknown geometry {geometry!r} for label {event.value.get('label')!r}"
        )


@pytest.mark.e2e
def test_tomato_lifecycle_positions_in_valid_zones(tomato_events) -> None:
    """Asset agent uses place_in_zone, so y must always land inside the zone map."""
    for event in [e for e in tomato_events if e.name == "scene:object_add"]:
        y = event.value["position"][1]
        assert -0.3 <= y <= 2.0, (
            f"y={y} outside [-0.3, 2.0] for label {event.value.get('label')!r}"
        )
