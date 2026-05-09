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
from collections.abc import Iterator
from pathlib import Path

from ag_ui.core import CustomEvent
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


def iter_asset_items(
    store: SceneStore, model: LLMClient
) -> Iterator[str | CustomEvent]:
    """Stream-friendly variant of `run_asset`.

    Yields one of:
      - `str` -- per-item progress narration ("asset: building cube (1/4)…")
        emitted BEFORE the LLM call for that item, so the chat updates while
        the LLM is in flight rather than after.
      - `CustomEvent` -- scene:object_add for the just-built item.

    The trailing summary narration ("asset: built 4 objects -- ...") is the
    caller's responsibility -- only it knows when iteration finishes.

    Used by:
      - `agent/main.py` for SSE streaming, driven via asyncio.to_thread per
        item so the asyncio loop can flush bytes between LLM calls.
      - `run_asset` (sync wrapper below) for tests and any non-streaming
        caller that just wants the final event list.
    """
    raw = store.get_brief()
    if not raw:
        return

    brief = Brief.model_validate(raw)
    zone_map = store.get_zone_map()
    total = len(brief.objectSummary)

    for index, item in enumerate(brief.objectSummary):
        yield f"asset: building {item.label} ({index + 1}/{total})…"

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
        yield make_object_add(payload)


def run_asset(store: SceneStore, model: LLMClient) -> AgentResult:
    if not store.get_brief():
        return AgentResult(narration="asset: skipped (no brief)")

    events: list[CustomEvent] = []
    labels: list[str] = []
    for item in iter_asset_items(store, model):
        if isinstance(item, CustomEvent):
            events.append(item)
            labels.append(item.value.get("label", "?"))
        # progress strings are only consumed by the streaming caller.

    if not labels:
        narration = "asset: nothing to build (empty objectSummary)"
    elif len(labels) == 1:
        narration = f"asset: built 1 object — {labels[0]}"
    elif len(labels) <= 3:
        narration = f"asset: built {len(labels)} objects — {', '.join(labels)}"
    else:
        head = ", ".join(labels[:3])
        narration = f"asset: built {len(labels)} objects — {head}, +{len(labels) - 3} more"

    return AgentResult(events=events, narration=narration)
