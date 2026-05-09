"""Layout agent: chooses camera + zone map and emits scene:camera_move.

Phase 2 rule: only emit a camera_move when the brief actually adds new
objects to the scene. A modification-only prompt ("move the cube up",
"remove the seed", "spin the camera") should leave the camera where it is
unless the Director explicitly asks otherwise via a future cameraAction.
"""

from __future__ import annotations

from agent.agents.types import AgentResult, Brief
from agent.events.scene_events import make_camera_move
from agent.store.scene_store import SceneStore
from shared.schema.sceneSchema import CameraMovePayload

CAMERA_PRESETS: dict[str, dict[str, tuple[float, float, float]]] = {
    "wide": {"position": (0.0, 1.5, 4.5), "target": (0.0, 0.8, 0.0)},
    "closeup": {"position": (0.0, 1.0, 1.8), "target": (0.0, 0.8, 0.0)},
    "orbit": {"position": (3.5, 1.5, 3.5), "target": (0.0, 0.8, 0.0)},
}


def run_layout(store: SceneStore) -> AgentResult:
    raw = store.get_brief()
    if not raw:
        return AgentResult(narration="layout: skipped (no brief)")

    brief = Brief.model_validate(raw)

    if not brief.objectSummary:
        # Modification-only prompt; preserve current camera framing.
        return AgentResult(narration="layout: kept (modify-only prompt)")

    preset = CAMERA_PRESETS.get(brief.cameraStyle, CAMERA_PRESETS["wide"])
    payload = CameraMovePayload(
        position=preset["position"],
        target=preset["target"],
        fov=50.0,
    )
    store.write_camera(payload.model_dump())
    pos = preset["position"]
    narration = (
        f"layout: {brief.cameraStyle} camera at "
        f"({pos[0]:g}, {pos[1]:g}, {pos[2]:g})"
    )
    return AgentResult(events=[make_camera_move(payload)], narration=narration)
