"""Controls agent: emits scene:control_panel when the brief asks for one.

Runs after Lighting (the last build-the-scene stage) so the panel renders
beneath the assistant's narration of what was just built. The Director
populates `brief.controlPanel` only when the user explicitly asked for
controls -- otherwise this stage is a no-op.

The agent doesn't construct controls itself; the Director already chose
what makes sense for the prompt + current scene. Controls is a thin
passthrough that preserves the Director's intent on the wire.
"""

from __future__ import annotations

from agent.agents.types import AgentResult, Brief
from agent.events.scene_events import make_control_panel
from agent.store.scene_store import SceneStore


def run_controls(store: SceneStore) -> AgentResult:
    raw = store.get_brief()
    if not raw:
        return AgentResult()

    brief = Brief.model_validate(raw)
    panel = brief.controlPanel
    if panel is None:
        return AgentResult()

    n = len(panel.controls)
    title = panel.title or panel.id
    return AgentResult(
        events=[make_control_panel(panel)],
        narration=(
            f"controls: '{title}' panel with {n} control{'s' if n != 1 else ''}"
        ),
    )
