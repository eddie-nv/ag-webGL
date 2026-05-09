"""Tests for the Lighting agent."""

from __future__ import annotations

from agent.agents.lighting import LIGHT_PRESETS, run_lighting
from agent.store.scene_store import SceneStore


def _store_with_mood(mood: str) -> SceneStore:
    store = SceneStore()
    store.write_brief(
        {
            "subject": "x",
            "stages": ["g"],
            "mood": mood,
            "cameraStyle": "wide",
            "estimatedObjectCount": 3,
            "objectSummary": [{"label": "x", "zone": "lower", "stage": "g"}],
        }
    )
    return store


def test_run_lighting_emits_preset_events_for_known_mood() -> None:
    result = run_lighting(_store_with_mood("earthy_warm"))
    expected_count = len(LIGHT_PRESETS["earthy_warm"])
    assert len(result.events) == expected_count
    assert {e.name for e in result.events} == {"scene:light_add"}


def test_run_lighting_unknown_mood_falls_back_to_default() -> None:
    result = run_lighting(_store_with_mood("intergalactic_disco"))
    assert len(result.events) == len(LIGHT_PRESETS["default"])


def test_run_lighting_no_brief_uses_default_preset() -> None:
    result = run_lighting(SceneStore())
    assert len(result.events) == len(LIGHT_PRESETS["default"])


def test_run_lighting_emits_at_least_two_lights_per_preset() -> None:
    for mood in LIGHT_PRESETS:
        result = run_lighting(_store_with_mood(mood))
        assert len(result.events) >= 2, f"preset {mood} has too few lights"
