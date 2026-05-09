"""LangGraph tool wrappers around SceneStore.

Each agent in the pipeline binds these tools to its LLM call so it can read
the current scene state and persist its own outputs.
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool, tool

from agent.store.scene_store import SceneStore


def create_store_tools(store: SceneStore) -> list[BaseTool]:
    @tool
    def get_manifest() -> dict[str, str]:
        """Return uuid -> label map for every object in the scene."""
        return store.get_manifest()

    @tool
    def get_object(uuid: str) -> dict[str, Any] | None:
        """Return the full payload of one object, or null if the uuid is unknown."""
        return store.get_object(uuid)

    @tool
    def get_objects(uuids: list[str]) -> list[dict[str, Any]]:
        """Batch-fetch full payloads for a list of uuids. Missing uuids are skipped."""
        return store.get_objects(uuids)

    @tool
    def get_zone_map() -> dict[str, Any]:
        """Return the spatial zone map (ground/lower/mid/upper with yRange)."""
        return store.get_zone_map()

    @tool
    def get_camera() -> dict[str, Any]:
        """Return the current camera state (position, target, optional fov)."""
        return store.get_camera()

    @tool
    def write_to_store(kind: str, payload: dict[str, Any]) -> str:
        """Persist data to the store.

        kind is one of: 'brief', 'object', 'camera'.
        For 'object', payload must contain a 'uuid' field.
        """
        if kind == "brief":
            store.write_brief(payload)
        elif kind == "object":
            uuid = payload.get("uuid")
            if not uuid:
                raise ValueError("object payload must contain a 'uuid' field")
            store.write_object(uuid, payload)
        elif kind == "camera":
            store.write_camera(payload)
        else:
            raise ValueError(f"unknown write kind: {kind!r}")
        return "ok"

    return [
        get_manifest,
        get_object,
        get_objects,
        get_zone_map,
        get_camera,
        write_to_store,
    ]
