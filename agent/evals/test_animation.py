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
    assert "static" in result.narration or "skipped" in result.narration


def test_run_animation_no_brief_skips() -> None:
    result = run_animation(SceneStore())
    assert result.events == []
    assert "no brief" in result.narration


def test_run_animation_empty_manifest_with_valid_brief() -> None:
    """animate=True + multi-stage but no objects in the manifest -- nothing
    to animate, narration just says skipped."""
    store = SceneStore()
    store.write_brief(_animated_brief(["s1", "s2"], animate=True))
    result = run_animation(store)
    assert result.events == []
    assert "skipped" in result.narration


def test_run_animation_emits_camera_spin_when_action_set() -> None:
    """`cameraAction.spin: true` emits a scene:animation_start with the
    sentinel uuid='camera' so the SceneController orbits the camera."""
    store = SceneStore()
    brief = _animated_brief(["only"], animate=False)
    brief["cameraAction"] = {"spin": True}
    store.write_brief(brief)

    result = run_animation(store)

    camera_events = [e for e in result.events if e.value["uuid"] == "camera"]
    assert len(camera_events) == 1
    assert camera_events[0].name == "scene:animation_start"
    assert "camera spinning" in result.narration


def test_run_animation_camera_spin_plus_object_rotate() -> None:
    """Camera spin and object rotation can coexist in a multi-stage,
    animate=True brief."""
    store = SceneStore()
    brief = _animated_brief(["s1", "s2"], animate=True)
    brief["cameraAction"] = {"spin": True}
    store.write_brief(brief)
    store.write_object("u1", {"label": "seed"})
    store.write_object("u2", {"label": "stem"})

    result = run_animation(store)

    uuids = {e.value["uuid"] for e in result.events}
    assert uuids == {"camera", "u1", "u2"}
    assert "camera spinning" in result.narration
    assert "rotating 2 objects" in result.narration


def test_run_animation_emits_camera_stop_when_action_set() -> None:
    """`cameraAction.stopSpin: true` produces scene:animation_stop with
    uuid='camera' so the AnimationLoop drops the orbit Tickable."""
    store = SceneStore()
    brief = _animated_brief(["only"], animate=False)
    brief["cameraAction"] = {"spin": False, "stopSpin": True}
    store.write_brief(brief)

    result = run_animation(store)

    stop_events = [e for e in result.events if e.name == "scene:animation_stop"]
    assert len(stop_events) == 1
    assert stop_events[0].value["uuid"] == "camera"
    assert "camera stop" in result.narration


def test_run_animation_camera_stop_then_start_in_one_brief() -> None:
    """When both stopSpin and spin are true, stop comes BEFORE start so the
    AnimationLoop sees a clean restart sequence."""
    store = SceneStore()
    brief = _animated_brief(["only"], animate=False)
    brief["cameraAction"] = {"spin": True, "stopSpin": True}
    store.write_brief(brief)

    result = run_animation(store)

    names = [e.name for e in result.events]
    assert names == ["scene:animation_stop", "scene:animation_start"]
    assert all(e.value["uuid"] == "camera" for e in result.events)
