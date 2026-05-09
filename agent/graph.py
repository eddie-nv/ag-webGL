"""Sequential LangGraph wiring: Director -> Layout -> Asset -> Animation -> Lighting.

V1 has no parallel branches and no conditional edges. The graph collects events
into the shared state and returns the final list to the caller.

`iter_pipeline` is the streaming variant the FastAPI server uses to interleave
per-agent narration with custom events; `run_pipeline` is the eager wrapper
the M5 / M8 tests still call.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TypedDict

from ag_ui.core import CustomEvent
from langgraph.graph import END, StateGraph

from agent.agents.animation import run_animation
from agent.agents.asset import run_asset
from agent.agents.director import run_director
from agent.agents.layout import run_layout
from agent.agents.lighting import run_lighting
from agent.agents.types import AgentResult, LLMClient
from agent.store.scene_store import SceneStore

AGENT_NAMES = ("director", "layout", "asset", "animation", "lighting")


class PipelineState(TypedDict):
    user_prompt: str
    events: list[CustomEvent]


def build_pipeline(store: SceneStore, model: LLMClient):
    graph = StateGraph(PipelineState)

    def director_node(state: PipelineState) -> PipelineState:
        result = run_director(state["user_prompt"], store, model)
        return {"events": state["events"] + result.events}

    def layout_node(state: PipelineState) -> PipelineState:
        result = run_layout(store)
        return {"events": state["events"] + result.events}

    def asset_node(state: PipelineState) -> PipelineState:
        result = run_asset(store, model)
        return {"events": state["events"] + result.events}

    def animation_node(state: PipelineState) -> PipelineState:
        result = run_animation(store)
        return {"events": state["events"] + result.events}

    def lighting_node(state: PipelineState) -> PipelineState:
        result = run_lighting(store)
        return {"events": state["events"] + result.events}

    graph.add_node("director", director_node)
    graph.add_node("layout", layout_node)
    graph.add_node("asset", asset_node)
    graph.add_node("animation", animation_node)
    graph.add_node("lighting", lighting_node)

    graph.set_entry_point("director")
    graph.add_edge("director", "layout")
    graph.add_edge("layout", "asset")
    graph.add_edge("asset", "animation")
    graph.add_edge("animation", "lighting")
    graph.add_edge("lighting", END)

    return graph.compile()


def run_pipeline(
    user_prompt: str,
    store: SceneStore,
    model: LLMClient,
) -> list[CustomEvent]:
    pipeline = build_pipeline(store, model)
    final = pipeline.invoke({"user_prompt": user_prompt, "events": []})
    return final["events"]


def iter_pipeline(
    user_prompt: str,
    store: SceneStore,
    model: LLMClient,
) -> Iterator[tuple[str, AgentResult]]:
    """Yield (agent_name, AgentResult) per stage so the HTTP layer can interleave
    narration with custom events on the wire.

    Calls each run_* function directly. The LangGraph build is overkill for v1's
    strictly sequential 5-step pipeline; using the plain generator keeps the
    streaming layer simple and avoids smuggling LangGraph's stream chunks
    through TypedDict-shaped state.
    """
    yield "director", run_director(user_prompt, store, model)
    yield "layout", run_layout(store)
    yield "asset", run_asset(store, model)
    yield "animation", run_animation(store)
    yield "lighting", run_lighting(store)
