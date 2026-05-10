"""Pydantic models for scene mutation event payloads.

Mirrors shared/schema/sceneSchema.ts. Source of truth for backend validation.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Vec3 = tuple[float, float, float]


class Material(BaseModel):
    type: str
    color: str


class ObjectAddPayload(BaseModel):
    uuid: str
    label: str
    geometryType: str
    geometryArgs: list[float]
    material: Material
    position: Vec3
    stage: str
    rotation: Vec3 | None = None
    scale: Vec3 | None = None
    visible: bool | None = None


class ObjectUpdatePayload(BaseModel):
    uuid: str
    position: Vec3 | None = None
    rotation: Vec3 | None = None
    scale: Vec3 | None = None
    material: Material | None = None


class ObjectRemovePayload(BaseModel):
    uuid: str


class CameraMovePayload(BaseModel):
    position: Vec3
    target: Vec3
    fov: float | None = None


LightType = Literal["DirectionalLight", "AmbientLight", "PointLight"]


class LightAddPayload(BaseModel):
    uuid: str
    lightType: LightType
    color: str
    intensity: float
    position: Vec3 | None = None


class AnimationStartPayload(BaseModel):
    """`from` is a Python keyword — stored as `from_` with JSON alias `from`."""

    model_config = ConfigDict(populate_by_name=True)

    uuid: str
    animationType: str
    duration: float
    axis: str | None = None
    from_: Vec3 | None = Field(default=None, alias="from")
    to: Vec3 | None = None
    loop: bool | None = None
    easing: str | None = None


class AnimationStopPayload(BaseModel):
    uuid: str


class EmitSpec(BaseModel):
    """One AG-UI custom event a control panel dispatches when activated.

    Matches the {name, value} shape of every other SSE custom event so the
    frontend can route it through the existing `routeSceneEvent` -- no
    special-case dispatch path for control-panel-driven events.
    """

    name: str
    value: dict[str, Any]


class ButtonControl(BaseModel):
    """One-shot button. Click fires every event in `emits` in order."""

    kind: Literal["button"] = "button"
    label: str
    emits: list[EmitSpec]


class ToggleControl(BaseModel):
    """Stateful toggle. `on` events fire when turning on, `off` events when
    turning off. The frontend tracks the toggle's local state."""

    kind: Literal["toggle"] = "toggle"
    label: str
    default: bool = False
    on: list[EmitSpec]
    off: list[EmitSpec]


# Discriminated union over `kind`. Adding a new control type later (slider,
# colorPicker) just adds a new model + extends the union.
Control = Annotated[
    ButtonControl | ToggleControl,
    Field(discriminator="kind"),
]


class ControlPanelPayload(BaseModel):
    """Inline UI rendered as a chat bubble. `id` is for identification only;
    the frontend keys panels by chat-message id."""

    id: str
    title: str | None = None
    controls: list[Control]
