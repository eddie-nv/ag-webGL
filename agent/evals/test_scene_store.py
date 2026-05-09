"""Tests for the in-memory SceneStore."""

from __future__ import annotations

from agent.store.scene_store import ZONE_MAP, SceneStore


def test_write_and_get_object() -> None:
    store = SceneStore()
    store.write_object(
        "u1",
        {"label": "leaf", "position": [0.0, 1.0, 0.0], "stage": "growth"},
    )
    obj = store.get_object("u1")
    assert obj is not None
    assert obj["label"] == "leaf"
    assert obj["stage"] == "growth"


def test_get_object_returns_none_for_missing() -> None:
    store = SceneStore()
    assert store.get_object("nonexistent") is None


def test_get_manifest_returns_labels_only() -> None:
    store = SceneStore()
    store.write_object("u1", {"label": "leaf", "position": [0.0, 1.0, 0.0]})
    store.write_object("u2", {"label": "stem", "position": [0.0, 0.0, 0.0]})

    manifest = store.get_manifest()

    assert manifest == {"u1": "leaf", "u2": "stem"}
    assert all(isinstance(value, str) for value in manifest.values())


def test_get_objects_batch_returns_all() -> None:
    store = SceneStore()
    store.write_object("u1", {"label": "a"})
    store.write_object("u2", {"label": "b"})
    store.write_object("u3", {"label": "c"})

    results = store.get_objects(["u1", "u3"])

    assert len(results) == 2
    assert {item["label"] for item in results} == {"a", "c"}


def test_get_objects_batch_skips_missing_uuids() -> None:
    store = SceneStore()
    store.write_object("u1", {"label": "a"})
    results = store.get_objects(["u1", "ghost"])
    assert len(results) == 1
    assert results[0]["label"] == "a"


def test_get_objects_by_stage_filters_correctly() -> None:
    store = SceneStore()
    store.write_object("u1", {"label": "a", "stage": "germination"})
    store.write_object("u2", {"label": "b", "stage": "growth"})
    store.write_object("u3", {"label": "c", "stage": "germination"})

    germ = store.get_objects_by_stage("germination")

    assert len(germ) == 2
    assert {item["label"] for item in germ} == {"a", "c"}


def test_get_objects_by_stage_returns_empty_for_unknown() -> None:
    store = SceneStore()
    store.write_object("u1", {"label": "a", "stage": "growth"})
    assert store.get_objects_by_stage("missing") == []


def test_zone_map_returns_four_zones() -> None:
    store = SceneStore()
    zones = store.get_zone_map()
    assert set(zones.keys()) == {"ground", "lower", "mid", "upper"}
    assert all("yRange" in zone for zone in zones.values())


def test_zone_map_constant_has_four_zones() -> None:
    assert set(ZONE_MAP.keys()) == {"ground", "lower", "mid", "upper"}


def test_write_brief_stores_brief() -> None:
    store = SceneStore()
    brief = {"subject": "tomato", "stages": ["germination", "growth"]}
    store.write_brief(brief)
    assert store.brief == brief


def test_get_camera_returns_camera_state() -> None:
    store = SceneStore()
    payload = {"position": [3.0, 2.0, 5.0], "target": [0.0, 0.0, 0.0]}
    store.write_camera(payload)
    assert store.get_camera() == payload


def test_get_camera_returns_empty_when_unset() -> None:
    store = SceneStore()
    assert store.get_camera() == {}


def test_write_object_does_not_alias_caller_dict() -> None:
    """Caller mutations after write must not affect stored state."""
    store = SceneStore()
    payload = {"label": "leaf"}
    store.write_object("u1", payload)
    payload["label"] = "stem"
    assert store.get_object("u1") == {"label": "leaf"}


def test_get_object_returns_copy() -> None:
    """Mutating the returned dict must not affect stored state."""
    store = SceneStore()
    store.write_object("u1", {"label": "leaf"})
    obj = store.get_object("u1")
    assert obj is not None
    obj["label"] = "mutated"
    assert store.get_object("u1") == {"label": "leaf"}


def test_get_zone_map_returns_copy() -> None:
    """Mutating the returned zone map must not affect future reads."""
    store = SceneStore()
    zones = store.get_zone_map()
    zones["ground"]["yRange"][0] = 999.0
    fresh = store.get_zone_map()
    assert fresh["ground"]["yRange"][0] != 999.0
