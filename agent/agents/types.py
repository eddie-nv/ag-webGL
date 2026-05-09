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
    estimatedObjectCount: int = Field(ge=3, le=30)
    objectSummary: list[ObjectSummaryItem]
