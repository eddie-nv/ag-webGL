"""Tests for the Controls agent + control panel schema."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent.agents.controls import run_controls
from agent.agents.types import Brief
from agent.store.scene_store import SceneStore
from shared.schema.sceneSchema import (
    ButtonControl,
    ControlPanelPayload,
    ToggleControl,
)


def _brief_with_panel(panel: dict | None) -> dict:
    base = {
        "subject": "blue_cube",
        "stages": ["static"],
        "mood": "default",
        "cameraStyle": "wide",
        "estimatedObjectCount": 0,
        "objectSummary": [],
        "updates": [],
        "removals": [],
        "cameraAction": None,
        "animate": False,
    }
    if panel is not None:
        base["controlPanel"] = panel
    return base


def test_run_controls_no_brief() -> None:
    result = run_controls(SceneStore())
    assert result.events == []
    assert result.narration == ""


def test_run_controls_brief_without_panel() -> None:
    """Brief.controlPanel = None -> agent is a no-op so the chat doesn't get
    a stray "controls: ..." bubble for every prompt."""
    store = SceneStore()
    store.write_brief(_brief_with_panel(None))
    result = run_controls(store)
    assert result.events == []
    assert result.narration == ""


def test_run_controls_emits_panel_event_when_set() -> None:
    panel = {
        "id": "default",
        "title": "Controls",
        "controls": [
            {
                "kind": "toggle",
                "label": "Spin camera",
                "default": False,
                "on": [
                    {
                        "name": "scene:animation_start",
                        "value": {
                            "uuid": "camera",
                            "animationType": "rotate",
                            "duration": 12,
                            "axis": "y",
                            "loop": True,
                        },
                    }
                ],
                "off": [
                    {"name": "scene:animation_stop", "value": {"uuid": "camera"}}
                ],
            },
            {
                "kind": "button",
                "label": "Delete cube",
                "emits": [
                    {"name": "scene:object_remove", "value": {"uuid": "u1"}}
                ],
            },
        ],
    }
    store = SceneStore()
    store.write_brief(_brief_with_panel(panel))

    result = run_controls(store)

    assert len(result.events) == 1
    event = result.events[0]
    assert event.name == "scene:control_panel"
    assert event.value["id"] == "default"
    assert len(event.value["controls"]) == 2
    # First control is a toggle, second is a button -- discriminator preserved.
    assert event.value["controls"][0]["kind"] == "toggle"
    assert event.value["controls"][1]["kind"] == "button"
    assert "2 controls" in result.narration


def test_brief_round_trips_control_panel() -> None:
    """Brief.controlPanel parses the discriminated union correctly."""
    payload = _brief_with_panel(
        {
            "id": "p",
            "controls": [
                {
                    "kind": "button",
                    "label": "X",
                    "emits": [{"name": "scene:object_remove", "value": {"uuid": "u"}}],
                }
            ],
        }
    )
    brief = Brief.model_validate(payload)
    assert brief.controlPanel is not None
    assert isinstance(brief.controlPanel.controls[0], ButtonControl)


def test_control_kind_discriminator_rejects_unknown() -> None:
    with pytest.raises(ValidationError):
        ControlPanelPayload.model_validate(
            {
                "id": "p",
                "controls": [{"kind": "slider", "label": "X"}],
            }
        )


def test_toggle_default_optional() -> None:
    """ToggleControl.default defaults to False per the schema."""
    t = ToggleControl(label="X", on=[], off=[])
    assert t.default is False
