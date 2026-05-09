"""Director agent: parses the user prompt into a structured Brief and writes it.

In v1 the brief drives every downstream agent deterministically, so it must
fully describe object identity, stages, and zone assignments.
"""

from __future__ import annotations

from pathlib import Path

from agent.agents.types import AgentResult, Brief, LLMClient
from agent.store.scene_store import SceneStore

# Re-exports kept for backward-compat with code/tests that imported from here.
__all__ = ["Brief", "run_director"]


_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "director.md"
_PROMPT_TEMPLATE = _PROMPT_PATH.read_text()


def _build_prompt(user_prompt: str) -> str:
    return _PROMPT_TEMPLATE.replace("{user_prompt}", user_prompt)


def run_director(prompt: str, store: SceneStore, model: LLMClient) -> AgentResult:
    """Parse the user prompt into a Brief and persist it.

    Raises pydantic.ValidationError if the LLM returns malformed JSON or a
    payload that violates the Brief schema. v1 does not retry; the graph
    surfaces the error to the caller.
    """
    raw = model.invoke(_build_prompt(prompt))
    brief = Brief.model_validate_json(raw)
    store.write_brief(brief.model_dump())
    return AgentResult()
