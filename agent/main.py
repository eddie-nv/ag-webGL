"""FastAPI server exposing the agent pipeline at POST /agui (AG-UI protocol).

The frontend's CopilotKit runtime (frontend/app/api/copilotkit/route.ts) wraps
an HttpAgent pointed at SCENE_AGENT_URL (default http://localhost:8000/agui).
This module is the thin HTTP layer that converts a user prompt into a stream
of AG-UI events (RunStarted -> custom mutation events -> RunFinished).

Run with:
    uvicorn agent.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
import os
import time
import traceback
import uuid
from collections.abc import AsyncIterator
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

from agent.graph import iter_pipeline
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
        message_id = str(uuid.uuid4())
        yield encoder.encode(TextMessageStartEvent(messageId=message_id, role="assistant"))
        yield encoder.encode(
            TextMessageContentEvent(messageId=message_id, delta="No prompt provided.")
        )
        yield encoder.encode(TextMessageEndEvent(messageId=message_id))
        yield encoder.encode(
            RunFinishedEvent(threadId=thread_id, runId=run_id, timestamp=_now_ms())
        )
        return

    # Opening bubble: confirm the prompt was received before the first LLM call
    # returns (~5-10s into the run).
    intro_id = str(uuid.uuid4())
    yield encoder.encode(TextMessageStartEvent(messageId=intro_id, role="assistant"))
    yield encoder.encode(
        TextMessageContentEvent(messageId=intro_id, delta="building the scene...")
    )
    yield encoder.encode(TextMessageEndEvent(messageId=intro_id))

    try:
        from agent.llm import AnthropicLLM

        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY not set on the agent server")

        store = SceneStore()
        model = AnthropicLLM()
        t0 = time.time()
        total_events = 0
        counts: dict[str, int] = {}

        for agent_name, result in iter_pipeline(user_prompt, store, model):
            # Per-agent narration bubble. messageId is fresh so the frontend
            # treats it as a new chat entry rather than appending.
            stage_id = str(uuid.uuid4())
            narration = result.narration or f"{agent_name}: done"
            yield encoder.encode(
                TextMessageStartEvent(messageId=stage_id, role="assistant")
            )
            yield encoder.encode(
                TextMessageContentEvent(messageId=stage_id, delta=narration)
            )
            yield encoder.encode(TextMessageEndEvent(messageId=stage_id))

            for event in result.events:
                log.debug("emit %s value_keys=%s", event.name, list(event.value.keys()))
                counts[event.name] = counts.get(event.name, 0) + 1
                total_events += 1
                yield encoder.encode(
                    CustomEvent(name=event.name, value=event.value, timestamp=_now_ms())
                )

        elapsed = time.time() - t0
        log.info(
            "pipeline ok elapsed=%.1fs total=%d %s",
            elapsed,
            total_events,
            ", ".join(f"{k}={v}" for k, v in sorted(counts.items())),
        )

        # Final summary bubble.
        done_id = str(uuid.uuid4())
        yield encoder.encode(TextMessageStartEvent(messageId=done_id, role="assistant"))
        yield encoder.encode(
            TextMessageContentEvent(
                messageId=done_id,
                delta=f"done — {total_events} event{'s' if total_events != 1 else ''} in {elapsed:.0f}s",
            )
        )
        yield encoder.encode(TextMessageEndEvent(messageId=done_id))
    except Exception as exc:
        log.error("pipeline failed: %s\n%s", exc, traceback.format_exc())
        err_id = str(uuid.uuid4())
        yield encoder.encode(TextMessageStartEvent(messageId=err_id, role="assistant"))
        yield encoder.encode(
            TextMessageContentEvent(messageId=err_id, delta=f"pipeline failed: {exc}")
        )
        yield encoder.encode(TextMessageEndEvent(messageId=err_id))

    yield encoder.encode(
        RunFinishedEvent(threadId=thread_id, runId=run_id, timestamp=_now_ms())
    )


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
