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


class AnchorSpec(BaseModel):
    """Place this item relative to another item in the same brief.

    The placement engine resolves `relativeTo` (a label, not a uuid) against
    items appearing earlier in `objectSummary`. When unresolvable -- the
    referenced label isn't in the brief, or it appears later -- the item
    falls back to grid placement.

    `offset` is added to the geometry-aware default clearance so the
    Director can fine-tune ("petals just above the stem" vs "well above").
    Units match scene units (meters in the y zones spanning -0.3..2.0).
    """

    relativeTo: str
    placement: Literal["above", "below", "left", "right", "front", "back", "on"] = "above"
    offset: float = 0.0


class ObjectSummaryItem(BaseModel):
    """Spec for a NEW object the Director wants Asset to add."""

    label: str
    zone: Zone
    stage: str
    # Optional spatial anchor against another label in the SAME brief. When
    # absent, placement uses grid (multi-subject) or centered stacking
    # (single-subject) heuristics. See agent/agents/placement.py.
    anchor: AnchorSpec | None = None


class BriefUpdate(BaseModel):
    """Spec for modifying an existing object the snapshot already includes.

    The Director outputs these when the user says "move the cube up", "make
    it bigger", "color it red", etc. Asset emits one scene:object_update per
    entry. Frontend's SceneController.updateObject locates by uuid and
    applies the diff in place -- no copy is made.

    `stopAnimation: True` makes Asset additionally emit a
    scene:animation_stop for this uuid -- "stop spinning the cube" without
    changing geometry/material.
    """

    uuid: str
    position: Vec3 | None = None
    rotation: Vec3 | None = None
    scale: Vec3 | None = None
    color: str | None = None  # convenience -- material type stays the same
    stopAnimation: bool = False


class CameraAction(BaseModel):
    """Camera-level commands the Director can issue alongside object changes.

    `spin: True` registers a camera-orbit Tickable on the AnimationLoop.
    `stopSpin: True` emits scene:animation_stop with uuid="camera" so the
    AnimationLoop drops the orbit Tickable. Setting both at once is treated
    as stop-then-start (Asset emits stop first, animator emits start after).
    """

    spin: bool = False
    stopSpin: bool = False


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
