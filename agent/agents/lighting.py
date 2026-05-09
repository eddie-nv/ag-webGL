"""Lighting agent: emits scene:light_add events per a mood preset.

V1 uses a small set of presets keyed off brief.mood with a default fallback.
LLM-driven lighting choices and per-zone light placement are v2.
"""

from __future__ import annotations

import uuid
from typing import Any

from agent.agents.types import AgentResult
from agent.events.scene_events import make_light_add
from agent.store.scene_store import SceneStore
from shared.schema.sceneSchema import LightAddPayload

LIGHT_PRESETS: dict[str, list[dict[str, Any]]] = {
    "earthy_warm": [
        {"lightType": "AmbientLight", "color": "#fff5e6", "intensity": 0.45},
        {
            "lightType": "DirectionalLight",
            "color": "#fff8d0",
            "intensity": 1.1,
            "position": (3.0, 5.0, 2.5),
        },
        {
            "lightType": "PointLight",
            "color": "#ffd4a0",
            "intensity": 0.6,
            "position": (-1.5, 2.0, 1.5),
        },
    ],
    "cool_clinical": [
        {"lightType": "AmbientLight", "color": "#e6f0ff", "intensity": 0.4},
        {
            "lightType": "DirectionalLight",
            "color": "#ffffff",
            "intensity": 1.2,
            "position": (3.0, 5.0, 2.5),
        },
    ],
    "default": [
        {"lightType": "AmbientLight", "color": "#ffffff", "intensity": 0.5},
        {
            "lightType": "DirectionalLight",
            "color": "#ffffff",
            "intensity": 1.0,
            "position": (3.0, 5.0, 2.5),
        },
    ],
}


def run_lighting(store: SceneStore) -> AgentResult:
    brief = store.get_brief()
    mood = brief.get("mood", "default") if brief else "default"
    presets = LIGHT_PRESETS.get(mood, LIGHT_PRESETS["default"])

    # model_validate (vs **spec unpack) gives a friendlier ValidationError if a
    # preset is ever extended with a key that isn't in LightAddPayload.
    events = [
        make_light_add(LightAddPayload.model_validate({"uuid": str(uuid.uuid4()), **spec}))
        for spec in presets
    ]
    return AgentResult(events=events)
