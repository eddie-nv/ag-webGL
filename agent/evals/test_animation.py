"""Tests for the Animation agent."""

from __future__ import annotations

from agent.agents.animation import DEFAULT_ROTATION_DURATION, run_animation
from agent.store.scene_store import SceneStore


def test_run_animation_emits_one_event_per_object() -> None:
    store = SceneStore()
    store.write_object("u1", {"label": "seed"})
    store.write_object("u2", {"label": "stem"})
    store.write_object("u3", {"label": "leaf"})

    result = run_animation(store)

    assert len(result.events) == 3
    assert {e.value["uuid"] for e in result.events} == {"u1", "u2", "u3"}
    assert {e.name for e in result.events} == {"scene:animation_start"}


def test_run_animation_uses_default_rotation() -> None:
    store = SceneStore()
    store.write_object("u1", {"label": "seed"})
    result = run_animation(store)
    payload = result.events[0].value
    assert payload["animationType"] == "rotate"
    assert payload["axis"] == "y"
    assert payload["loop"] is True
    assert payload["duration"] == DEFAULT_ROTATION_DURATION


def test_run_animation_empty_manifest() -> None:
    assert run_animation(SceneStore()).events == []
