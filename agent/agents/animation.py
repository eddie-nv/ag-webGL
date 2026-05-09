"""Animation agent: emits a scene:animation_start per object in the manifest.

V1 applies a slow y-axis rotation to every object IF the brief opted in via
`brief.animate` AND the brief has more than one stage (single-stage scenes
are static by default -- "make a blue cube" should not spin).
Per-object animation selection (grow, drift, oscillate, ...) is v2.
"""

from __future__ import annotations

from agent.agents.types import AgentResult, Brief
from agent.events.scene_events import make_animation_start
from agent.store.scene_store import SceneStore
from shared.schema.sceneSchema import AnimationStartPayload

DEFAULT_ROTATION_DURATION = 6.0


def run_animation(store: SceneStore) -> AgentResult:
    raw = store.get_brief()
    if not raw:
        return AgentResult(narration="animation: skipped (no brief)")

    brief = Brief.model_validate(raw)
    if not brief.animate:
        return AgentResult(narration="animation: skipped (static scene)")
    if len(brief.stages) <= 1:
        return AgentResult(narration="animation: skipped (single-stage scene)")

    manifest = store.get_manifest()
    events = [
        make_animation_start(
            AnimationStartPayload(
                uuid=obj_uuid,
                animationType="rotate",
                duration=DEFAULT_ROTATION_DURATION,
                axis="y",
                loop=True,
            )
        )
        for obj_uuid in manifest
    ]
    narration = (
        f"animation: rotating {len(events)} object{'s' if len(events) != 1 else ''}"
        if events
        else "animation: nothing to animate (empty manifest)"
    )
    return AgentResult(events=events, narration=narration)
