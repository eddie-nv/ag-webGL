"""Asset agent: per brief item, asks the LLM for geometry+material details.

Position is assigned deterministically by `place_in_zone` so zone evals are
verifiable without hitting a real model. Geometry/material remain LLM choices.

Failure semantics (v1): if the LLM returns malformed JSON for any item, this
function raises pydantic.ValidationError without rolling back the items
already written to the store. Callers receive a partial scene state. M8 will
add retry/repair around real-model calls.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from pydantic import BaseModel

from agent.agents.placement import place_in_zone
from agent.agents.types import AgentResult, Brief, LLMClient
from agent.events.scene_events import make_object_add
from agent.store.scene_store import SceneStore
from shared.schema.sceneSchema import Material, ObjectAddPayload


class AssetDetails(BaseModel):
    geometryType: str
    geometryArgs: list[float]
    material: Material


_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "asset.md"
_PROMPT_TEMPLATE = _PROMPT_PATH.read_text()


def _build_prompt(label: str, zone: str, stage: str) -> str:
    return (
        _PROMPT_TEMPLATE.replace("{label}", label)
        .replace("{zone}", zone)
        .replace("{stage}", stage)
    )


def run_asset(store: SceneStore, model: LLMClient) -> AgentResult:
    raw = store.get_brief()
    if not raw:
        return AgentResult()

    brief = Brief.model_validate(raw)
    zone_map = store.get_zone_map()

    events = []
    for index, item in enumerate(brief.objectSummary):
        details_json = model.invoke(_build_prompt(item.label, item.zone, item.stage))
        details = AssetDetails.model_validate_json(details_json)

        position = place_in_zone(item.zone, zone_map, index)
        payload = ObjectAddPayload(
            uuid=str(uuid.uuid4()),
            label=item.label,
            geometryType=details.geometryType,
            geometryArgs=details.geometryArgs,
            material=details.material,
            position=position,
            stage=item.stage,
        )
        store.write_object(payload.uuid, payload.model_dump())
        events.append(make_object_add(payload))

    return AgentResult(events=events)
