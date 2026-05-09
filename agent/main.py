"""FastAPI server exposing the agent pipeline at POST /agui (AG-UI protocol).

The frontend POSTs here via /api/agui (a thin Next.js proxy). This module is
the HTTP layer that converts a user prompt into a stream of AG-UI events:
RunStarted -> per-stage TextMessage* + custom mutation events -> RunFinished.

Streaming model (Phase 1):

  - Each agent's *intent* is narrated BEFORE the agent runs ("director: parsing
    the prompt..."), then the agent runs in a worker thread via
    `asyncio.to_thread` so the asyncio loop stays alive and can flush each
    yielded SSE chunk to the network as it goes.
  - The Asset stage drives `iter_asset_items` one item at a time (next() in a
    worker thread) so per-object progress narration and scene:object_add
    events arrive incrementally rather than in a clump at the end.

Run with:
    uvicorn agent.main:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import traceback
import uuid
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

from ag_ui.core.events import (
    CustomEvent,
    RunFinishedEvent,
    RunStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
)
from ag_ui.encoder.encoder import EventEncoder
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

from agent.agents.animation import run_animation
from agent.agents.asset import iter_asset_items
from agent.agents.director import run_director
from agent.agents.layout import run_layout
from agent.agents.lighting import run_lighting
from agent.store.scene_store import SceneStore

# Auto-load .env at the project root.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("scene")

app = FastAPI(title="scene-agent-system")


@app.get("/")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


def _extract_user_prompt(payload: dict[str, Any]) -> str:
    """Pull the latest user message text out of an AG-UI run input."""
    messages = payload.get("messages", [])
    for message in reversed(messages):
        if message.get("role") == "user":
            content = message.get("content", "")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return "".join(
                    part.get("text", "")
                    for part in content
                    if isinstance(part, dict) and part.get("type") == "text"
                )
    return ""


def _now_ms() -> int:
    return int(time.time() * 1000)


def _safe_next(iterator: Iterator[Any]) -> tuple[Any, bool]:
    """next() that returns (value, done_flag) so it crosses the
    `asyncio.to_thread` boundary without raising StopIteration in the loop."""
    try:
        return next(iterator), False
    except StopIteration:
        return None, True


async def _bubble(encoder: EventEncoder, text: str) -> AsyncIterator[str]:
    """Encode one self-contained assistant chat bubble (start + content + end)."""
    msg_id = str(uuid.uuid4())
    yield encoder.encode(TextMessageStartEvent(messageId=msg_id, role="assistant"))
    yield encoder.encode(TextMessageContentEvent(messageId=msg_id, delta=text))
    yield encoder.encode(TextMessageEndEvent(messageId=msg_id))


def _emit_custom(
    encoder: EventEncoder,
    event: CustomEvent,
    counts: dict[str, int],
) -> str:
    """Re-stamp the timestamp on the way out and update the counter."""
    counts[event.name] = counts.get(event.name, 0) + 1
    return encoder.encode(
        CustomEvent(name=event.name, value=event.value, timestamp=_now_ms())
    )


async def _stream_pipeline(payload: dict[str, Any]) -> AsyncIterator[str]:
    encoder = EventEncoder()
    thread_id = payload.get("threadId") or str(uuid.uuid4())
    run_id = payload.get("runId") or str(uuid.uuid4())
    user_prompt = _extract_user_prompt(payload)

    log.info("run start thread=%s run=%s prompt=%r", thread_id, run_id, user_prompt[:120])

    yield encoder.encode(
        RunStartedEvent(threadId=thread_id, runId=run_id, timestamp=_now_ms())
    )

    if not user_prompt:
        log.warning("empty user_prompt; payload keys=%s", list(payload.keys()))
        async for chunk in _bubble(encoder, "no prompt provided."):
            yield chunk
        yield encoder.encode(
            RunFinishedEvent(threadId=thread_id, runId=run_id, timestamp=_now_ms())
        )
        return

    # Opening bubble appears immediately so the user sees something before the
    # first LLM call returns (~5-10s in).
    async for chunk in _bubble(encoder, "building the scene…"):
        yield chunk

    try:
        from agent.llm import AnthropicLLM

        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY not set on the agent server")

        store = SceneStore()
        model = AnthropicLLM()
        t0 = time.time()
        counts: dict[str, int] = {}

        # ---- Director ----
        async for chunk in _bubble(encoder, "director: parsing the prompt…"):
            yield chunk
        director_result = await asyncio.to_thread(run_director, user_prompt, store, model)
        async for chunk in _bubble(encoder, director_result.narration):
            yield chunk
        for event in director_result.events:
            yield _emit_custom(encoder, event, counts)

        # ---- Layout (deterministic, no LLM) ----
        layout_result = await asyncio.to_thread(run_layout, store)
        async for chunk in _bubble(encoder, layout_result.narration):
            yield chunk
        for event in layout_result.events:
            yield _emit_custom(encoder, event, counts)

        # ---- Asset (per-item streaming) ----
        asset_labels: list[str] = []
        item_iter = iter_asset_items(store, model)
        while True:
            item, done = await asyncio.to_thread(_safe_next, item_iter)
            if done:
                break
            if isinstance(item, str):
                async for chunk in _bubble(encoder, item):
                    yield chunk
            else:  # CustomEvent (scene:object_add)
                asset_labels.append(item.value.get("label", "?"))
                yield _emit_custom(encoder, item, counts)

        async for chunk in _bubble(encoder, _asset_summary(asset_labels)):
            yield chunk

        # ---- Animation ----
        animation_result = await asyncio.to_thread(run_animation, store)
        async for chunk in _bubble(encoder, animation_result.narration):
            yield chunk
        for event in animation_result.events:
            yield _emit_custom(encoder, event, counts)

        # ---- Lighting ----
        lighting_result = await asyncio.to_thread(run_lighting, store)
        async for chunk in _bubble(encoder, lighting_result.narration):
            yield chunk
        for event in lighting_result.events:
            yield _emit_custom(encoder, event, counts)

        elapsed = time.time() - t0
        total = sum(counts.values())
        log.info(
            "pipeline ok elapsed=%.1fs total=%d %s",
            elapsed,
            total,
            ", ".join(f"{k}={v}" for k, v in sorted(counts.items())),
        )

        async for chunk in _bubble(
            encoder,
            f"done — {total} event{'s' if total != 1 else ''} in {elapsed:.0f}s",
        ):
            yield chunk

    except Exception as exc:
        log.error("pipeline failed: %s\n%s", exc, traceback.format_exc())
        async for chunk in _bubble(encoder, f"pipeline failed: {exc}"):
            yield chunk

    yield encoder.encode(
        RunFinishedEvent(threadId=thread_id, runId=run_id, timestamp=_now_ms())
    )


def _asset_summary(labels: list[str]) -> str:
    if not labels:
        return "asset: nothing to build (empty objectSummary)"
    if len(labels) == 1:
        return f"asset: built 1 object — {labels[0]}"
    if len(labels) <= 3:
        return f"asset: built {len(labels)} objects — {', '.join(labels)}"
    head = ", ".join(labels[:3])
    return f"asset: built {len(labels)} objects — {head}, +{len(labels) - 3} more"


@app.post("/agui")
async def agui(request: Request) -> StreamingResponse:
    payload = await request.json()
    log.info(
        "POST /agui keys=%s message_count=%d",
        list(payload.keys()),
        len(payload.get("messages", [])),
    )
    return StreamingResponse(
        _stream_pipeline(payload),
        media_type="text/event-stream",
    )
