"""Zone placement evals (M5 plan: 4 required tests + supporting cases)."""

from __future__ import annotations

import json

import pytest

from agent.agents.asset import iter_asset_items, run_asset
from agent.agents.placement import place_in_zone
from agent.store.scene_store import ZONE_MAP, SceneStore


class StubLLM:
    """Returns the same canned response for every invocation."""

    def __init__(self, response: str | dict) -> None:
        self.response = response if isinstance(response, str) else json.dumps(response)
        self.invocations: int = 0

    def invoke(self, prompt: str) -> str:
        self.invocations += 1
        return self.response


def _asset_response() -> str:
    return json.dumps(
        {
            "geometryType": "SphereGeometry",
            "geometryArgs": [0.1, 16, 16],
            "material": {"type": "MeshStandardMaterial", "color": "#5b3a1a"},
        }
    )


def test_position_in_declared_zone() -> None:
    for zone, spec in ZONE_MAP.items():
        position = place_in_zone(zone, ZONE_MAP, index=0)
        y = position[1]
        y_lo, y_hi = spec["yRange"]
        assert y_lo <= y <= y_hi, f"y={y} not in {zone} range [{y_lo}, {y_hi}]"


def test_position_not_in_wrong_zone() -> None:
    """The placement for `ground` must not land inside any other zone's yRange."""
    position = place_in_zone("ground", ZONE_MAP, index=0)
    y = position[1]
    upper_lo, upper_hi = ZONE_MAP["upper"]["yRange"]
    mid_lo, mid_hi = ZONE_MAP["mid"]["yRange"]
    assert not (upper_lo < y < upper_hi)
    assert not (mid_lo < y < mid_hi)


def test_place_in_zone_unknown_raises() -> None:
    with pytest.raises(ValueError, match="unknown zone"):
        place_in_zone("stratosphere", ZONE_MAP)


def test_place_in_zone_spreads_x_with_index() -> None:
    a = place_in_zone("lower", ZONE_MAP, index=0)
    b = place_in_zone("lower", ZONE_MAP, index=1)
    assert a != b
    assert a[1] == b[1]  # same zone -> same y


def test_asset_agent_emits_object_add_per_brief_item() -> None:
    store = SceneStore()
    store.write_brief(
        {
            "subject": "tomato",
            "stages": ["germination", "growth", "fruiting"],
            "mood": "earthy_warm",
            "cameraStyle": "wide",
            "estimatedObjectCount": 4,
            "objectSummary": [
                {"label": "seed", "zone": "ground", "stage": "germination"},
                {"label": "stem", "zone": "lower", "stage": "growth"},
                {"label": "leaf", "zone": "mid", "stage": "growth"},
                {"label": "tomato", "zone": "upper", "stage": "fruiting"},
            ],
        }
    )
    llm = StubLLM(_asset_response())

    result = run_asset(store, llm)

    assert llm.invocations == 4
    assert len(result.events) == 4
    assert {event.name for event in result.events} == {"scene:object_add"}


def test_asset_agent_with_empty_object_summary_emits_nothing() -> None:
    store = SceneStore()
    store.write_brief(
        {
            "subject": "x",
            "stages": ["g"],
            "mood": "default",
            "cameraStyle": "wide",
            "estimatedObjectCount": 3,
            "objectSummary": [],
        }
    )
    llm = StubLLM(_asset_response())
    # estimatedObjectCount must be >= 3 to satisfy the schema, but objectSummary
    # can still be empty -- the agent must short-circuit cleanly.
    result = run_asset(store, llm)
    assert llm.invocations == 0
    assert result.events == []


def test_run_asset_emits_animation_stop_for_object_update() -> None:
    """Phase 5: an update entry with stopAnimation=True produces
    scene:animation_stop for that uuid; a no-diff update doesn't emit a
    redundant object_update."""
    store = SceneStore()
    store.write_object("u1", {"label": "cube"})
    store.write_brief(
        {
            "subject": "x",
            "stages": ["static"],
            "mood": "default",
            "cameraStyle": "wide",
            "estimatedObjectCount": 0,
            "objectSummary": [],
            "updates": [{"uuid": "u1", "stopAnimation": True}],
            "removals": [],
            "cameraAction": None,
            "animate": False,
        }
    )

    result = run_asset(store, StubLLM(_asset_response()))

    stop_events = [e for e in result.events if e.name == "scene:animation_stop"]
    assert len(stop_events) == 1
    assert stop_events[0].value["uuid"] == "u1"
    update_events = [e for e in result.events if e.name == "scene:object_update"]
    assert update_events == []
    assert "stopped 1" in result.narration


def test_run_asset_skips_unknown_uuids() -> None:
    """Phase 5: Director hallucinated a uuid not in the snapshot. Asset
    must not emit a CustomEvent for it; chat narration mentions it."""
    store = SceneStore()
    store.write_object("u1", {"label": "cube"})
    store.write_brief(
        {
            "subject": "x",
            "stages": ["static"],
            "mood": "default",
            "cameraStyle": "wide",
            "estimatedObjectCount": 0,
            "objectSummary": [],
            "updates": [{"uuid": "ghost", "position": [1, 2, 3]}],
            "removals": ["another-ghost"],
            "cameraAction": None,
            "animate": False,
        }
    )

    items = list(iter_asset_items(store, StubLLM(_asset_response())))
    narrations = [x for x in items if isinstance(x, str)]
    events = [x for x in items if not isinstance(x, str)]

    assert events == []
    assert any("unknown uuid" in n for n in narrations)


def test_asset_agent_positions_match_declared_zones() -> None:
    store = SceneStore()
    store.write_brief(
        {
            "subject": "tomato",
            "stages": ["g"],
            "mood": "earthy_warm",
            "cameraStyle": "wide",
            "estimatedObjectCount": 4,
            "objectSummary": [
                {"label": "seed", "zone": "ground", "stage": "g"},
                {"label": "root", "zone": "ground", "stage": "g"},
                {"label": "stem_lo", "zone": "lower", "stage": "g"},
                {"label": "stem_mid", "zone": "mid", "stage": "g"},
                {"label": "leaf_up", "zone": "upper", "stage": "g"},
            ],
        }
    )
    llm = StubLLM(_asset_response())

    result = run_asset(store, llm)

    for event, item in zip(result.events, store.brief["objectSummary"], strict=True):
        zone = item["zone"]
        y_lo, y_hi = ZONE_MAP[zone]["yRange"]
        y = event.value["position"][1]
        assert y_lo <= y <= y_hi, f"{event.value['label']} y={y} outside {zone}"
