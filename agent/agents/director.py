"""Director agent: parses the user prompt into a structured Brief and writes it.

Phase 2: the Director also receives the *current* scene snapshot (uuid -> label
manifest) so it can plan additions, updates, removals, and camera actions
against existing state -- not just from-scratch creation.
"""

from __future__ import annotations

from pathlib import Path

from agent.agents.types import AgentResult, Brief, LLMClient
from agent.store.scene_store import SceneStore

# Re-exports kept for backward-compat with code/tests that imported from here.
__all__ = ["Brief", "run_director"]


_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "director.md"
_PROMPT_TEMPLATE = _PROMPT_PATH.read_text()


def _format_scene_state(manifest: dict[str, str]) -> str:
    if not manifest:
        return "  (empty scene -- this is the first prompt)"
    return "\n".join(f"  - {uuid}: {label}" for uuid, label in manifest.items())


def _build_prompt(user_prompt: str, manifest: dict[str, str]) -> str:
    return _PROMPT_TEMPLATE.replace("{user_prompt}", user_prompt).replace(
        "{scene_state}", _format_scene_state(manifest)
    )


def _build_narration(brief: Brief) -> str:
    parts: list[str] = []
    if brief.objectSummary:
        parts.append(f"+{len(brief.objectSummary)}")
    if brief.updates:
        parts.append(f"~{len(brief.updates)}")
    if brief.removals:
        parts.append(f"-{len(brief.removals)}")
    if brief.cameraAction and brief.cameraAction.spin:
        parts.append("camera spin")
    if brief.animate:
        parts.append("animated")
    suffix = " ".join(parts) if parts else "no-op"
    return f"director: planned {brief.subject} ({suffix})"


def run_director(prompt: str, store: SceneStore, model: LLMClient) -> AgentResult:
    """Parse the user prompt + current scene into a Brief and persist it.

    Raises pydantic.ValidationError if the LLM returns malformed JSON or a
    payload that violates the Brief schema. v1 does not retry; the graph
    surfaces the error to the caller.
    """
    manifest = store.get_manifest()
    raw = model.invoke(_build_prompt(prompt, manifest))
    brief = Brief.model_validate_json(raw)
    store.write_brief(brief.model_dump())
    return AgentResult(narration=_build_narration(brief))
