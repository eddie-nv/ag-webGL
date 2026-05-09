"""Tests for the Director agent."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from agent.agents.director import Brief, run_director
from agent.store.scene_store import SceneStore


class StubLLM:
    def __init__(self, response: str) -> None:
        self.response = response
        self.last_prompt: str | None = None

    def invoke(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self.response


def _valid_brief_dict() -> dict:
    return {
        "subject": "tomato_plant",
        "stages": ["germination", "growth", "fruiting"],
        "mood": "earthy_warm",
        "cameraStyle": "wide",
        "estimatedObjectCount": 4,
        "objectSummary": [
            {"label": "seed", "zone": "ground", "stage": "germination"},
            {"label": "stem", "zone": "lower", "stage": "growth"},
            {"label": "leaf", "zone": "mid", "stage": "growth"},
            {"label": "tomato", "zone": "upper", "stage": "fruiting"},
        ],
    }


def test_run_director_writes_brief_to_store() -> None:
    store = SceneStore()
    llm = StubLLM(json.dumps(_valid_brief_dict()))

    result = run_director("Walk me through a tomato plant's lifecycle", store, llm)

    assert result.events == []
    assert result.narration  # narration set for the chat-bubble narrator
    assert "tomato_plant" in result.narration
    assert store.brief["subject"] == "tomato_plant"
    assert store.brief["estimatedObjectCount"] == 4
    assert llm.last_prompt is not None
    assert "Walk me through a tomato plant's lifecycle" in llm.last_prompt


def test_run_director_rejects_invalid_camera_style() -> None:
    bad = {**_valid_brief_dict(), "cameraStyle": "panorama"}
    store = SceneStore()
    llm = StubLLM(json.dumps(bad))

    with pytest.raises(ValidationError):
        run_director("any", store, llm)


def test_run_director_rejects_invalid_zone() -> None:
    bad = _valid_brief_dict()
    bad["objectSummary"][0]["zone"] = "stratosphere"
    store = SceneStore()
    llm = StubLLM(json.dumps(bad))

    with pytest.raises(ValidationError):
        run_director("any", store, llm)


def test_brief_enforces_object_count_bounds() -> None:
    """Lower bound is 0 (modify-only / remove-only / camera-only prompts);
    upper is 30."""
    one_object = {
        **_valid_brief_dict(),
        "estimatedObjectCount": 1,
        "objectSummary": [
            {"label": "cube", "zone": "lower", "stage": "germination"}
        ],
    }
    Brief.model_validate(one_object)  # must not raise

    zero_objects = {
        **_valid_brief_dict(),
        "estimatedObjectCount": 0,
        "objectSummary": [],
    }
    Brief.model_validate(zero_objects)  # must not raise (Phase 2)

    negative = {**_valid_brief_dict(), "estimatedObjectCount": -1}
    too_many = {**_valid_brief_dict(), "estimatedObjectCount": 999}

    with pytest.raises(ValidationError):
        Brief.model_validate(negative)

    with pytest.raises(ValidationError):
        Brief.model_validate(too_many)


def test_brief_animate_defaults_to_false() -> None:
    """A brief that doesn't mention `animate` (older clients / forgetful LLM)
    is treated as static."""
    brief = Brief.model_validate(_valid_brief_dict())
    assert brief.animate is False


def test_brief_round_trips_animate_true() -> None:
    payload = {**_valid_brief_dict(), "animate": True}
    brief = Brief.model_validate(payload)
    assert brief.animate is True
