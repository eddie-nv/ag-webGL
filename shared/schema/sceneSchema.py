"""Pydantic models for scene mutation event payloads.

Mirrors shared/schema/sceneSchema.ts. Source of truth for backend validation.
"""

from __future__ import annotations

from typing import Literal

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
