"""Validation tests for scene event payloads (Pydantic schemas)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from shared.schema.sceneSchema import (
    AnimationStartPayload,
    AnimationStopPayload,
    CameraMovePayload,
    LightAddPayload,
    ObjectAddPayload,
    ObjectUpdatePayload,
)


def _valid_object_add() -> dict:
    return {
        "uuid": "obj-1",
        "label": "tomato_seed",
        "geometryType": "SphereGeometry",
        "geometryArgs": [0.05, 16, 16],
        "material": {"type": "MeshStandardMaterial", "color": "#5b3a1a"},
        "position": [0.0, -0.1, 0.0],
        "stage": "germination",
    }


def test_object_add_requires_uuid() -> None:
    payload = _valid_object_add()
    del payload["uuid"]
    with pytest.raises(ValidationError):
        ObjectAddPayload.model_validate(payload)


def test_object_add_requires_geometry_type() -> None:
    payload = _valid_object_add()
    del payload["geometryType"]
    with pytest.raises(ValidationError):
        ObjectAddPayload.model_validate(payload)


def test_object_add_valid_payload_passes() -> None:
    parsed = ObjectAddPayload.model_validate(_valid_object_add())
    assert parsed.uuid == "obj-1"
    assert parsed.geometryType == "SphereGeometry"
    assert list(parsed.position) == [0.0, -0.1, 0.0]
    assert parsed.material.color == "#5b3a1a"
    assert parsed.stage == "germination"


def test_object_add_position_must_have_three_elements() -> None:
    payload = _valid_object_add()
    payload["position"] = [0.0, 0.0]
    with pytest.raises(ValidationError):
        ObjectAddPayload.model_validate(payload)


def test_object_update_requires_uuid() -> None:
    with pytest.raises(ValidationError):
        ObjectUpdatePayload.model_validate({"position": [1, 2, 3]})

    parsed = ObjectUpdatePayload.model_validate({"uuid": "obj-1"})
    assert parsed.uuid == "obj-1"
    assert parsed.position is None


def test_camera_move_requires_position_and_target() -> None:
    with pytest.raises(ValidationError):
        CameraMovePayload.model_validate({"position": [3, 2, 5]})

    with pytest.raises(ValidationError):
        CameraMovePayload.model_validate({"target": [0, 0, 0]})

    parsed = CameraMovePayload.model_validate(
        {"position": [3, 2, 5], "target": [0, 0, 0]}
    )
    assert list(parsed.position) == [3, 2, 5]
    assert list(parsed.target) == [0, 0, 0]


def test_light_add_valid_types_only() -> None:
    valid = {
        "uuid": "light-1",
        "lightType": "DirectionalLight",
        "color": "#ffffff",
        "intensity": 1.2,
    }
    parsed = LightAddPayload.model_validate(valid)
    assert parsed.lightType == "DirectionalLight"

    with pytest.raises(ValidationError):
        LightAddPayload.model_validate({**valid, "lightType": "SpotLight"})

    parsed_ambient = LightAddPayload.model_validate(
        {**valid, "lightType": "AmbientLight"}
    )
    assert parsed_ambient.lightType == "AmbientLight"


def test_animation_start_requires_duration() -> None:
    payload = {"uuid": "obj-1", "animationType": "rotate"}
    with pytest.raises(ValidationError):
        AnimationStartPayload.model_validate(payload)

    parsed = AnimationStartPayload.model_validate({**payload, "duration": 2.5})
    assert parsed.duration == 2.5


def test_animation_stop_requires_uuid() -> None:
    with pytest.raises(ValidationError):
        AnimationStopPayload.model_validate({})

    parsed = AnimationStopPayload.model_validate({"uuid": "obj-1"})
    assert parsed.uuid == "obj-1"
