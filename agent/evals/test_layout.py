"""Tests for the Layout agent."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent.agents.layout import CAMERA_PRESETS, run_layout
from agent.store.scene_store import SceneStore


def _store_with_brief(camera_style: str = "wide") -> SceneStore:
    store = SceneStore()
    store.write_brief(
        {
            "subject": "tomato",
            "stages": ["g"],
            "mood": "earthy_warm",
            "cameraStyle": camera_style,
            "estimatedObjectCount": 3,
            "objectSummary": [{"label": "x", "zone": "lower", "stage": "g"}],
        }
    )
    return store


def test_run_layout_emits_one_camera_move_event() -> None:
    result = run_layout(_store_with_brief("wide"))
    assert len(result.events) == 1
    assert result.events[0].name == "scene:camera_move"


def test_run_layout_writes_camera_to_store() -> None:
    store = _store_with_brief("wide")
    run_layout(store)
    camera = store.get_camera()
    assert "position" in camera
    assert "target" in camera
    assert camera["fov"] == 50.0


def test_run_layout_camera_position_matches_style() -> None:
    for style in ("wide", "closeup", "orbit"):
        store = _store_with_brief(style)
        result = run_layout(store)
        emitted = result.events[0].value
        expected = CAMERA_PRESETS[style]
        assert tuple(emitted["position"]) == expected["position"]


def test_run_layout_rejects_invalid_camera_style() -> None:
    """Brief.cameraStyle is a Literal; an unknown value must fail loudly at the
    layout boundary rather than silently falling back. (Production briefs come
    from the Director, which already validates -- this guards bypass scenarios.)"""
    store = _store_with_brief("not_a_real_style")
    with pytest.raises(ValidationError):
        run_layout(store)


def test_run_layout_no_brief_emits_nothing() -> None:
    result = run_layout(SceneStore())
    assert result.events == []
