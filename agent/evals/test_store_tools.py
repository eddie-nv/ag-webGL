"""Tests for LangGraph tool wrappers around SceneStore."""

from __future__ import annotations

import pytest

from agent.store.scene_store import SceneStore
from agent.store.store_tools import create_store_tools


def _tool_named(tools, name):
    return next(t for t in tools if t.name == name)


def test_create_store_tools_returns_six_tools() -> None:
    tools = create_store_tools(SceneStore())
    names = {t.name for t in tools}
    assert names == {
        "get_manifest",
        "get_object",
        "get_objects",
        "get_zone_map",
        "get_camera",
        "write_to_store",
    }


def test_get_manifest_tool_proxies_store() -> None:
    store = SceneStore()
    store.write_object("u1", {"label": "leaf"})
    tools = create_store_tools(store)

    result = _tool_named(tools, "get_manifest").invoke({})

    assert result == {"u1": "leaf"}


def test_get_object_tool_proxies_store() -> None:
    store = SceneStore()
    store.write_object("u1", {"label": "leaf"})
    tools = create_store_tools(store)

    result = _tool_named(tools, "get_object").invoke({"uuid": "u1"})

    assert result == {"label": "leaf"}


def test_get_zone_map_tool_returns_four_zones() -> None:
    tools = create_store_tools(SceneStore())
    zones = _tool_named(tools, "get_zone_map").invoke({})
    assert set(zones.keys()) == {"ground", "lower", "mid", "upper"}


def test_write_to_store_persists_object() -> None:
    store = SceneStore()
    tools = create_store_tools(store)
    _tool_named(tools, "write_to_store").invoke(
        {"kind": "object", "payload": {"uuid": "u1", "label": "leaf"}}
    )
    assert store.get_object("u1") == {"uuid": "u1", "label": "leaf"}


def test_write_to_store_object_requires_uuid() -> None:
    store = SceneStore()
    tools = create_store_tools(store)
    write = _tool_named(tools, "write_to_store")
    with pytest.raises(ValueError, match="uuid"):
        write.invoke({"kind": "object", "payload": {"label": "leaf"}})


def test_write_to_store_persists_brief_and_camera() -> None:
    store = SceneStore()
    tools = create_store_tools(store)
    write = _tool_named(tools, "write_to_store")

    write.invoke({"kind": "brief", "payload": {"subject": "tomato"}})
    write.invoke(
        {"kind": "camera", "payload": {"position": [3, 2, 5], "target": [0, 0, 0]}}
    )

    assert store.brief == {"subject": "tomato"}
    assert store.get_camera() == {"position": [3, 2, 5], "target": [0, 0, 0]}


def test_write_to_store_unknown_kind_raises() -> None:
    store = SceneStore()
    tools = create_store_tools(store)
    write = _tool_named(tools, "write_to_store")
    with pytest.raises(ValueError, match="unknown"):
        write.invoke({"kind": "noun", "payload": {}})
