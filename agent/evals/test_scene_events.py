"""Smoke tests for AG-UI CustomEvent wrappers in agent/events/scene_events.py."""

from __future__ import annotations

from agent.events.scene_events import (
    make_animation_start,
    make_animation_stop,
    make_camera_move,
    make_light_add,
    make_object_add,
    make_object_update,
)
from agent.events.vocabulary import (
    SCENE_ANIMATION_START,
    SCENE_ANIMATION_STOP,
    SCENE_CAMERA_MOVE,
    SCENE_LIGHT_ADD,
    SCENE_OBJECT_ADD,
    SCENE_OBJECT_UPDATE,
)
from shared.schema.sceneSchema import (
    AnimationStartPayload,
    AnimationStopPayload,
    CameraMovePayload,
    LightAddPayload,
    ObjectAddPayload,
    ObjectUpdatePayload,
)


def _object_add() -> ObjectAddPayload:
    return ObjectAddPayload.model_validate(
        {
            "uuid": "obj-1",
            "label": "tomato_seed",
            "geometryType": "SphereGeometry",
            "geometryArgs": [0.05, 16, 16],
            "material": {"type": "MeshStandardMaterial", "color": "#5b3a1a"},
            "position": [0.0, -0.1, 0.0],
            "stage": "germination",
        }
    )


def test_make_object_add_returns_custom_event() -> None:
    event = make_object_add(_object_add())
    assert event.name == SCENE_OBJECT_ADD
    assert event.value["uuid"] == "obj-1"
    assert event.value["geometryType"] == "SphereGeometry"


def test_make_object_add_excludes_unset_optional_fields() -> None:
    event = make_object_add(_object_add())
    # rotation/scale/visible were not provided; they should not appear in the wire payload.
    assert "rotation" not in event.value
    assert "scale" not in event.value
    assert "visible" not in event.value


def test_make_object_update_returns_custom_event() -> None:
    payload = ObjectUpdatePayload.model_validate(
        {"uuid": "obj-1", "position": [1.0, 2.0, 3.0]}
    )
    event = make_object_update(payload)
    assert event.name == SCENE_OBJECT_UPDATE
    assert event.value == {"uuid": "obj-1", "position": (1.0, 2.0, 3.0)}


def test_make_camera_move_returns_custom_event() -> None:
    payload = CameraMovePayload.model_validate(
        {"position": [3.0, 2.0, 5.0], "target": [0.0, 0.0, 0.0]}
    )
    event = make_camera_move(payload)
    assert event.name == SCENE_CAMERA_MOVE
    assert event.value["position"] == (3.0, 2.0, 5.0)
    assert event.value["target"] == (0.0, 0.0, 0.0)


def test_make_light_add_returns_custom_event() -> None:
    payload = LightAddPayload.model_validate(
        {
            "uuid": "light-1",
            "lightType": "DirectionalLight",
            "color": "#ffffff",
            "intensity": 1.2,
        }
    )
    event = make_light_add(payload)
    assert event.name == SCENE_LIGHT_ADD
    assert event.value["lightType"] == "DirectionalLight"


def test_make_animation_start_emits_from_alias() -> None:
    """Pydantic stores `from` as `from_`; wire payload must use `from`."""
    payload = AnimationStartPayload.model_validate(
        {
            "uuid": "obj-1",
            "animationType": "translate",
            "duration": 1.5,
            "from": [0.0, 0.0, 0.0],
            "to": [1.0, 1.0, 1.0],
        }
    )
    event = make_animation_start(payload)
    assert event.name == SCENE_ANIMATION_START
    assert "from" in event.value
    assert "from_" not in event.value
    assert event.value["from"] == (0.0, 0.0, 0.0)


def test_make_animation_stop_returns_custom_event() -> None:
    event = make_animation_stop(AnimationStopPayload.model_validate({"uuid": "obj-1"}))
    assert event.name == SCENE_ANIMATION_STOP
    assert event.value == {"uuid": "obj-1"}
