"""Animation agent: emits a scene:animation_start per object in the manifest.

V1 applies a slow y-axis rotation to every object; per-object animation
selection (grow, drift, oscillate, ...) is v2.
"""

from __future__ import annotations

from agent.agents.types import AgentResult
from agent.events.scene_events import make_animation_start
from agent.store.scene_store import SceneStore
from shared.schema.sceneSchema import AnimationStartPayload

DEFAULT_ROTATION_DURATION = 6.0


def run_animation(store: SceneStore) -> AgentResult:
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
    return AgentResult(events=events)
