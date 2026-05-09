"""Typed AG-UI CustomEvent wrappers for scene mutations.

Each helper validates the payload via its Pydantic model and serializes it to
the dict shape AG-UI streams to the frontend.
"""

from __future__ import annotations

from ag_ui.core import CustomEvent

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


def make_object_add(payload: ObjectAddPayload) -> CustomEvent:
    return CustomEvent(
        name=SCENE_OBJECT_ADD,
        value=payload.model_dump(exclude_none=True),
    )


def make_object_update(payload: ObjectUpdatePayload) -> CustomEvent:
    return CustomEvent(
        name=SCENE_OBJECT_UPDATE,
        value=payload.model_dump(exclude_none=True),
    )


def make_camera_move(payload: CameraMovePayload) -> CustomEvent:
    return CustomEvent(
        name=SCENE_CAMERA_MOVE,
        value=payload.model_dump(exclude_none=True),
    )


def make_light_add(payload: LightAddPayload) -> CustomEvent:
    return CustomEvent(
        name=SCENE_LIGHT_ADD,
        value=payload.model_dump(exclude_none=True),
    )


def make_animation_start(payload: AnimationStartPayload) -> CustomEvent:
    # by_alias=True so the JSON keyword `from` is emitted (stored as from_ in Python)
    return CustomEvent(
        name=SCENE_ANIMATION_START,
        value=payload.model_dump(exclude_none=True, by_alias=True),
    )


def make_animation_stop(payload: AnimationStopPayload) -> CustomEvent:
    return CustomEvent(
        name=SCENE_ANIMATION_STOP,
        value=payload.model_dump(exclude_none=True),
    )
