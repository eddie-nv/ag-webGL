"""Tests for the Animation agent."""

from __future__ import annotations

from agent.agents.animation import DEFAULT_ROTATION_DURATION, run_animation
from agent.store.scene_store import SceneStore


def _animated_brief(stages: list[str], animate: bool = True) -> dict:
    return {
        "subject": "x",
        "stages": stages,
        "mood": "default",
        "cameraStyle": "wide",
        "estimatedObjectCount": 3,
        "objectSummary": [
            {"label": "a", "zone": "lower", "stage": stages[0]},
        ],
        "animate": animate,
    }


def test_run_animation_emits_one_event_per_object_when_animate_true_multistage() -> None:
    store = SceneStore()
    store.write_brief(_animated_brief(["seed", "growth", "fruit"], animate=True))
    store.write_object("u1", {"label": "seed"})
    store.write_object("u2", {"label": "stem"})
    store.write_object("u3", {"label": "leaf"})

    result = run_animation(store)

    assert len(result.events) == 3
    assert {e.value["uuid"] for e in result.events} == {"u1", "u2", "u3"}
    assert {e.name for e in result.events} == {"scene:animation_start"}
    assert "rotating 3" in result.narration


def test_run_animation_uses_default_rotation() -> None:
    store = SceneStore()
    store.write_brief(_animated_brief(["seed", "growth"], animate=True))
    store.write_object("u1", {"label": "seed"})

    result = run_animation(store)
    payload = result.events[0].value

    assert payload["animationType"] == "rotate"
    assert payload["axis"] == "y"
    assert payload["loop"] is True
    assert payload["duration"] == DEFAULT_ROTATION_DURATION


def test_run_animation_skips_when_animate_false() -> None:
    store = SceneStore()
    store.write_brief(_animated_brief(["s1", "s2"], animate=False))
    store.write_object("u1", {"label": "seed"})

    result = run_animation(store)

    assert result.events == []
    assert "static" in result.narration


def test_run_animation_skips_when_single_stage() -> None:
    """Even with animate=True, a single-stage brief is treated as static --
    nothing temporal to animate over."""
    store = SceneStore()
    store.write_brief(_animated_brief(["only_stage"], animate=True))
    store.write_object("u1", {"label": "seed"})

    result = run_animation(store)

    assert result.events == []
    assert "single-stage" in result.narration


def test_run_animation_no_brief_skips() -> None:
    result = run_animation(SceneStore())
    assert result.events == []
    assert "no brief" in result.narration


def test_run_animation_empty_manifest_with_valid_brief() -> None:
    store = SceneStore()
    store.write_brief(_animated_brief(["s1", "s2"], animate=True))
    result = run_animation(store)
    assert result.events == []
    assert "empty manifest" in result.narration
