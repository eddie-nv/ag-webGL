"""Asset agent: per brief item, asks the LLM for geometry+material details
and emits scene mutation events.

In Phase 2 the brief carries three lists -- additions (new objects),
updates (mutate existing), removals (uuids to delete). iter_asset_items
walks all three, yielding per-item progress narration interleaved with
CustomEvents so the SSE stream produces visible progress.

Failure semantics (v1): if the LLM returns malformed JSON for any addition,
this function raises pydantic.ValidationError without rolling back items
already written to the store. Callers receive a partial scene state.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path

from ag_ui.core import CustomEvent
from pydantic import BaseModel

from agent.agents.placement import Placer
from agent.agents.types import AgentResult, Brief, LLMClient
from agent.events.scene_events import (
    make_animation_stop,
    make_object_add,
    make_object_remove,
    make_object_update,
)
from agent.store.scene_store import SceneStore
from shared.schema.sceneSchema import (
    AnimationStopPayload,
    Material,
    ObjectAddPayload,
    ObjectRemovePayload,
    ObjectUpdatePayload,
)


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


def _label_for(store: SceneStore, target_uuid: str) -> str:
    obj = store.get_object(target_uuid)
    return (obj or {}).get("label") or target_uuid[:8]


def iter_asset_items(
    store: SceneStore, model: LLMClient
) -> Iterator[str | CustomEvent]:
    """Stream the asset stage one item at a time.

    Yield order:
      1. removals first -- they reduce the manifest the Director may have
         referenced for adjacent positioning.
      2. updates next -- they touch existing objects in place.
      3. additions last -- new objects can take any uuids freed up.

    Each item yields a `str` (per-item progress narration) BEFORE the work,
    then a `CustomEvent` after. Caller (agent/main.py) wraps each next() in
    asyncio.to_thread so the asyncio loop keeps flushing while LLM calls
    block.
    """
    raw = store.get_brief()
    if not raw:
        return

    brief = Brief.model_validate(raw)

    # ---- removals (no LLM, deterministic) ----
    for target_uuid in brief.removals:
        if store.get_object(target_uuid) is None:
            # Director referenced a uuid the snapshot didn't contain. Surface
            # the hallucination as a chat-visible note instead of silently
            # no-oping.
            yield f"asset: skip remove (unknown uuid {target_uuid[:8]})"
            continue
        label = _label_for(store, target_uuid)
        yield f"asset: removing {label}…"
        yield make_object_remove(ObjectRemovePayload(uuid=target_uuid))

    # ---- updates (no LLM, deterministic) ----
    for upd in brief.updates:
        if store.get_object(upd.uuid) is None:
            yield f"asset: skip update (unknown uuid {upd.uuid[:8]})"
            continue
        label = _label_for(store, upd.uuid)

        # Per-object stop wins over per-object diff -- if the user said
        # "stop spinning the cube" alongside a position change, the diff
        # still applies; we just additionally drop the Tickable.
        if upd.stopAnimation:
            yield f"asset: stopping animation on {label}"
            yield make_animation_stop(AnimationStopPayload(uuid=upd.uuid))

        # Only emit object_update if there's actually something to change.
        has_diff = any(
            v is not None for v in (upd.position, upd.rotation, upd.scale, upd.color)
        )
        if not has_diff:
            continue

        yield f"asset: updating {label}…"
        material = (
            Material(type="MeshStandardMaterial", color=upd.color)
            if upd.color
            else None
        )
        yield make_object_update(
            ObjectUpdatePayload(
                uuid=upd.uuid,
                position=upd.position,
                rotation=upd.rotation,
                scale=upd.scale,
                material=material,
            )
        )

    # ---- additions (LLM-driven) ----
    zone_map = store.get_zone_map()
    placer = Placer(brief.objectSummary, zone_map)
    total = len(brief.objectSummary)
    for index, item in enumerate(brief.objectSummary):
        yield f"asset: building {item.label} ({index + 1}/{total})…"

        details_json = model.invoke(_build_prompt(item.label, item.zone, item.stage))
        details = AssetDetails.model_validate_json(details_json)

        # Anchored / stacked / grid placement is decided here based on the
        # full brief context + the geometry the LLM just chose for this item.
        position = placer.place(index, item, details.geometryType, details.geometryArgs)
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
    """Eager wrapper used by tests and any non-streaming caller."""
    if not store.get_brief():
        return AgentResult(narration="asset: skipped (no brief)")

    events: list[CustomEvent] = []
    add_labels: list[str] = []
    update_count = 0
    remove_count = 0
    for item in iter_asset_items(store, model):
        if not isinstance(item, CustomEvent):
            continue
        events.append(item)
        if item.name == "scene:object_add":
            add_labels.append(item.value.get("label", "?"))
        elif item.name == "scene:object_update":
            update_count += 1
        elif item.name == "scene:object_remove":
            remove_count += 1

    narration = _summarize(add_labels, update_count, remove_count)
    return AgentResult(events=events, narration=narration)


def run_asset(store: SceneStore, model: LLMClient) -> AgentResult:
    """Eager wrapper used by tests and any non-streaming caller."""
    if not store.get_brief():
        return AgentResult(narration="asset: skipped (no brief)")

    events: list[CustomEvent] = []
    add_labels: list[str] = []
    update_count = 0
    remove_count = 0
    stop_count = 0
    for item in iter_asset_items(store, model):
        if not isinstance(item, CustomEvent):
            continue
        events.append(item)
        if item.name == "scene:object_add":
            add_labels.append(item.value.get("label", "?"))
        elif item.name == "scene:object_update":
            update_count += 1
        elif item.name == "scene:object_remove":
            remove_count += 1
        elif item.name == "scene:animation_stop":
            stop_count += 1

    narration = _summarize(add_labels, update_count, remove_count, stop_count)
    return AgentResult(events=events, narration=narration)


def _summarize(
    add_labels: list[str],
    update_count: int,
    remove_count: int,
    stop_count: int = 0,
) -> str:
    parts: list[str] = []
    if add_labels:
        if len(add_labels) == 1:
            parts.append(f"built 1 — {add_labels[0]}")
        elif len(add_labels) <= 3:
            parts.append(f"built {len(add_labels)} — {', '.join(add_labels)}")
        else:
            head = ", ".join(add_labels[:3])
            parts.append(
                f"built {len(add_labels)} — {head}, +{len(add_labels) - 3} more"
            )
    if update_count:
        parts.append(f"updated {update_count}")
    if remove_count:
        parts.append(f"removed {remove_count}")
    if stop_count:
        parts.append(f"stopped {stop_count}")
    if not parts:
        return "asset: nothing to do (empty brief)"
    return "asset: " + ", ".join(parts)
