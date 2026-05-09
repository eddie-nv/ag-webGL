"""Shared types for the agent pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from ag_ui.core import CustomEvent
from pydantic import BaseModel, Field

from shared.schema.sceneSchema import Material, Vec3


class LLMClient(Protocol):
    """Minimal protocol the pipeline uses to call out to a model.

    Production wraps a langchain ChatModel. Tests pass a deterministic stub.
    """

    def invoke(self, prompt: str) -> str: ...


@dataclass
class AgentResult:
    events: list[CustomEvent] = field(default_factory=list)
    narration: str = ""


CameraStyle = Literal["wide", "closeup", "orbit"]
Zone = Literal["ground", "lower", "mid", "upper"]


class ObjectSummaryItem(BaseModel):
    """Spec for a NEW object the Director wants Asset to add."""

    label: str
    zone: Zone
    stage: str


class BriefUpdate(BaseModel):
    """Spec for modifying an existing object the snapshot already includes.

    The Director outputs these when the user says "move the cube up", "make
    it bigger", "color it red", etc. Asset emits one scene:object_update per
    entry. Frontend's SceneController.updateObject locates by uuid and
    applies the diff in place -- no copy is made.
    """

    uuid: str
    position: Vec3 | None = None
    rotation: Vec3 | None = None
    scale: Vec3 | None = None
    color: str | None = None  # convenience -- material type stays the same


class CameraAction(BaseModel):
    """Camera-level commands the Director can issue alongside object changes.

    `spin: True` registers a camera-orbit Tickable on the AnimationLoop. Stops
    only on explicit scene:animation_stop with uuid="camera" (or full reload).
    """

    spin: bool = False


class Brief(BaseModel):
    subject: str
    stages: list[str]
    mood: str
    cameraStyle: CameraStyle
    # 0 is valid: a "remove the cube" or "spin the camera" prompt has no
    # additions but is still a legitimate brief. Upper bound stays 30.
    estimatedObjectCount: int = Field(ge=0, le=30)
    # Additions (existing field name preserved for back-compat with M5 tests).
    objectSummary: list[ObjectSummaryItem] = Field(default_factory=list)
    # Modifications to existing scene objects.
    updates: list[BriefUpdate] = Field(default_factory=list)
    # uuids of objects to remove from the scene.
    removals: list[str] = Field(default_factory=list)
    # Optional camera-level command alongside object changes.
    cameraAction: CameraAction | None = None
    # True only when the user described a process / change over time.
    animate: bool = False
