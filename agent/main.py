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

from agent.graph import run_pipeline
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

    # The narrative message that streams alongside the scene mutations.
    message_id = str(uuid.uuid4())
    yield encoder.encode(TextMessageStartEvent(messageId=message_id, role="assistant"))
    yield encoder.encode(
        TextMessageContentEvent(messageId=message_id, delta="Building the scene...")
    )

    try:
        from agent.llm import AnthropicLLM

        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY not set on the agent server")

        store = SceneStore()
        t0 = time.time()
        events = run_pipeline(user_prompt, store, AnthropicLLM())
        elapsed = time.time() - t0
        counts: dict[str, int] = {}
        for e in events:
            counts[e.name] = counts.get(e.name, 0) + 1
        log.info(
            "pipeline ok elapsed=%.1fs total=%d %s",
            elapsed,
            len(events),
            ", ".join(f"{k}={v}" for k, v in sorted(counts.items())),
        )

        for event in events:
            log.debug("emit %s value_keys=%s", event.name, list(event.value.keys()))
            yield encoder.encode(
                CustomEvent(name=event.name, value=event.value, timestamp=_now_ms())
            )

        yield encoder.encode(
            TextMessageContentEvent(
                messageId=message_id,
                delta=f" Done -- {len(events)} events emitted.",
            )
        )
    except Exception as exc:
        log.error("pipeline failed: %s\n%s", exc, traceback.format_exc())
        yield encoder.encode(
            TextMessageContentEvent(
                messageId=message_id, delta=f" Pipeline failed: {exc}"
            )
        )

    yield encoder.encode(TextMessageEndEvent(messageId=message_id))
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
