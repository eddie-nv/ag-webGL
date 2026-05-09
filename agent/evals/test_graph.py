"""End-to-end (mocked-LLM) test for the sequential agent graph."""

from __future__ import annotations

import json

from agent.evals.fixtures.expected_events import TOMATO_EXPECTED
from agent.graph import AGENT_NAMES, iter_pipeline, run_pipeline
from agent.store.scene_store import SceneStore


class CycleStubLLM:
    """Returns scripted responses based on which call number it is.

    Director gets the first call (returns the brief). Asset receives one call
    per objectSummary item (returns the same asset details for simplicity).
    """

    def __init__(self, brief: str, asset: str) -> None:
        self._brief = brief
        self._asset = asset
        self._call = 0

    def invoke(self, prompt: str) -> str:
        self._call += 1
        if self._call == 1:
            return self._brief
        return self._asset


def _brief_response() -> str:
    return json.dumps(
        {
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
            "animate": True,
        }
    )


def _asset_response() -> str:
    return json.dumps(
        {
            "geometryType": "SphereGeometry",
            "geometryArgs": [0.1, 16, 16],
            "material": {"type": "MeshStandardMaterial", "color": "#5b3a1a"},
        }
    )


def test_pipeline_runs_all_five_agents_in_order() -> None:
    store = SceneStore()
    llm = CycleStubLLM(_brief_response(), _asset_response())

    events = run_pipeline("Walk me through a tomato plant's lifecycle", store, llm)

    counts: dict[str, int] = {}
    for e in events:
        counts[e.name] = counts.get(e.name, 0) + 1

    assert counts.get("scene:camera_move", 0) >= TOMATO_EXPECTED["scene:camera_move"]["min"]
    assert counts.get("scene:object_add", 0) >= TOMATO_EXPECTED["scene:object_add"]["min"]
    assert counts.get("scene:object_add", 0) <= TOMATO_EXPECTED["scene:object_add"]["max"]
    assert counts.get("scene:light_add", 0) >= TOMATO_EXPECTED["scene:light_add"]["min"]
    assert counts.get("scene:animation_start", 0) >= TOMATO_EXPECTED["scene:animation_start"]["min"]


def test_pipeline_writes_brief_objects_and_camera_to_store() -> None:
    store = SceneStore()
    llm = CycleStubLLM(_brief_response(), _asset_response())

    run_pipeline("Walk me through a tomato plant's lifecycle", store, llm)

    assert store.brief["subject"] == "tomato_plant"
    assert len(store.objects) == 4
    assert "position" in store.get_camera()


def test_iter_pipeline_yields_each_agent_with_narration() -> None:
    store = SceneStore()
    llm = CycleStubLLM(_brief_response(), _asset_response())

    stages = list(iter_pipeline("any prompt", store, llm))

    names = [name for name, _ in stages]
    assert tuple(names) == AGENT_NAMES
    for name, result in stages:
        assert isinstance(result.narration, str) and result.narration, (
            f"agent {name!r} returned empty narration"
        )


def test_iter_pipeline_static_brief_skips_animation() -> None:
    """When the brief is single-stage and animate=False, the animation agent
    should yield zero events with a 'skipped' narration."""
    static_brief = json.dumps(
        {
            "subject": "blue_cube",
            "stages": ["static"],
            "mood": "default",
            "cameraStyle": "wide",
            "estimatedObjectCount": 1,
            "objectSummary": [{"label": "cube", "zone": "lower", "stage": "static"}],
            "animate": False,
        }
    )
    store = SceneStore()
    llm = CycleStubLLM(static_brief, _asset_response())

    stages = dict(iter_pipeline("make a blue cube", store, llm))

    assert stages["animation"].events == []
    assert "skipped" in stages["animation"].narration
    # Sanity check: asset built exactly one object.
    assert len(stages["asset"].events) == 1
