"""Animation agent: emits scene:animation_start events.

Two animation paths in v1:

1. Camera spin -- if `brief.cameraAction.spin` is True, emit one event with
   `uuid="camera"`. SceneController recognises the magic uuid and registers
   a camera-orbit Tickable instead of an object Tickable.

2. Object rotation -- if `brief.animate` is True AND the brief is multi-stage,
   emit one rotate Tickable per object in the manifest. Single-stage scenes
   ("make a blue cube") stay static even with animate=True so the user
   doesn't see things spinning unexpectedly.

Per-object animation selection (grow / drift / oscillate) is v2.
"""

from __future__ import annotations

from agent.agents.types import AgentResult, Brief
from agent.events.scene_events import make_animation_start, make_animation_stop
from agent.store.scene_store import SceneStore
from shared.schema.sceneSchema import AnimationStartPayload, AnimationStopPayload

DEFAULT_ROTATION_DURATION = 6.0
CAMERA_ORBIT_DURATION = 12.0
CAMERA_UUID = "camera"


def run_animation(store: SceneStore) -> AgentResult:
    raw = store.get_brief()
    if not raw:
        return AgentResult(narration="animation: skipped (no brief)")

    brief = Brief.model_validate(raw)
    events = []
    parts: list[str] = []

    # Camera stop has to come BEFORE start so a "stop then re-spin" prompt
    # produces a clean restart on the AnimationLoop.
    if brief.cameraAction and brief.cameraAction.stopSpin:
        events.append(make_animation_stop(AnimationStopPayload(uuid=CAMERA_UUID)))
        parts.append("camera stop")

    # Camera spin (independent of object animation)
    if brief.cameraAction and brief.cameraAction.spin:
        events.append(
            make_animation_start(
                AnimationStartPayload(
                    uuid=CAMERA_UUID,
                    animationType="rotate",
                    duration=CAMERA_ORBIT_DURATION,
                    axis="y",
                    loop=True,
                )
            )
        )
        parts.append("camera spinning")

    # Object rotation only when explicitly requested AND multi-stage.
    if brief.animate and len(brief.stages) > 1:
        manifest = store.get_manifest()
        for obj_uuid in manifest:
            events.append(
                make_animation_start(
                    AnimationStartPayload(
                        uuid=obj_uuid,
                        animationType="rotate",
                        duration=DEFAULT_ROTATION_DURATION,
                        axis="y",
                        loop=True,
                    )
                )
            )
        if manifest:
            parts.append(f"rotating {len(manifest)} objects")

    if not parts:
        return AgentResult(events=[], narration="animation: skipped (static scene)")
    return AgentResult(events=events, narration="animation: " + ", ".join(parts))
