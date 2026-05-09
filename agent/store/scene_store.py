"""In-memory scene store queryable by the agent pipeline.

V1 is intentionally a simple dict-of-dicts. Per the immutability rule, the
store deep-copies on every write and read so callers can never accidentally
alias internal state.
"""

from __future__ import annotations

import copy
from typing import Any

# MOCK: replace in v2 with bounding-box computation derived from real geometry
ZONE_MAP: dict[str, dict[str, list[float]]] = {
    "ground": {"yRange": [-0.3, 0.0]},
    "lower": {"yRange": [0.0, 0.6]},
    "mid": {"yRange": [0.6, 1.2]},
    "upper": {"yRange": [1.2, 2.0]},
}


class SceneStore:
    def __init__(self) -> None:
        self.brief: dict[str, Any] = {}
        self.objects: dict[str, dict[str, Any]] = {}
        self.camera: dict[str, Any] = {}
        self.zone_map: dict[str, Any] = {}  # MOCK: hardcoded zones
        self.current_stage: str = ""
        self.stages_completed: list[str] = []
        self.stages_remaining: list[str] = []

    def write_brief(self, brief: dict[str, Any]) -> None:
        self.brief = copy.deepcopy(brief)

    def write_object(self, uuid: str, payload: dict[str, Any]) -> None:
        self.objects[uuid] = copy.deepcopy(payload)

    def write_camera(self, payload: dict[str, Any]) -> None:
        self.camera = copy.deepcopy(payload)

    def get_brief(self) -> dict[str, Any]:
        return copy.deepcopy(self.brief)

    def get_manifest(self) -> dict[str, str]:
        return {uuid: obj.get("label", "") for uuid, obj in self.objects.items()}

    def get_object(self, uuid: str) -> dict[str, Any] | None:
        obj = self.objects.get(uuid)
        return copy.deepcopy(obj) if obj is not None else None

    def get_objects(self, uuids: list[str]) -> list[dict[str, Any]]:
        # MOCK: loop -- replace in v2 with a true batch fetch
        results: list[dict[str, Any]] = []
        for uuid in uuids:
            obj = self.get_object(uuid)
            if obj is not None:
                results.append(obj)
        return results

    def get_zone_map(self) -> dict[str, Any]:
        # MOCK: hardcoded -- replace in v2 with computed zones
        return copy.deepcopy(ZONE_MAP)

    def get_camera(self) -> dict[str, Any]:
        return copy.deepcopy(self.camera)

    def get_objects_by_stage(self, stage: str) -> list[dict[str, Any]]:
        # MOCK: filter -- replace in v2 with a stage index
        return [
            copy.deepcopy(obj)
            for obj in self.objects.values()
            if obj.get("stage") == stage
        ]
