"""Shared types for the agent pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from ag_ui.core import CustomEvent
from pydantic import BaseModel, Field


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
    label: str
    zone: Zone
    stage: str


class Brief(BaseModel):
    subject: str
    stages: list[str]
    mood: str
    cameraStyle: CameraStyle
    # Lower bound is 1 so a "make a blue cube" prompt yields a single-item brief
    # rather than padding to three. Animation/multi-stage logic keys off `animate`.
    estimatedObjectCount: int = Field(ge=1, le=30)
    objectSummary: list[ObjectSummaryItem]
    # Director declares whether the scene should animate. Defaults to False so a
    # forgetful or older-prompt brief produces a static scene rather than spinning
    # everything by accident.
    animate: bool = False
