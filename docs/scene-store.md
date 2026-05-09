# Scene Store

In-memory state shared across the agent pipeline. One `SceneStore` per run;
no persistence in v1.

## API

```python
class SceneStore:
    # Writes (always deep-copy the input)
    def write_brief(self, brief: dict) -> None
    def write_object(self, uuid: str, payload: dict) -> None
    def write_camera(self, payload: dict) -> None

    # Reads (always return deep copies)
    def get_brief(self) -> dict
    def get_object(self, uuid: str) -> dict | None
    def get_objects(self, uuids: list[str]) -> list[dict]
    def get_objects_by_stage(self, stage: str) -> list[dict]
    def get_manifest(self) -> dict[str, str]   # uuid -> label
    def get_camera(self) -> dict
    def get_zone_map(self) -> dict
```

Plus public attributes inherited from the M2 plan signature: `brief`,
`objects`, `camera`, `zone_map`, `current_stage`, `stages_completed`,
`stages_remaining`. Tests read these directly; production code should prefer
the `get_*` accessors so the deep-copy guarantee holds.

## Immutability invariant

Every read returns a fresh `copy.deepcopy(...)`. Every write deep-copies
the caller's dict before storing. This means:

- A caller mutating its own dict after `write_object` does **not** affect
  the stored state.
- A caller mutating the dict returned by `get_object` does **not** affect
  the stored state or future reads.

Violations would corrupt agent context silently (the agent would see
state that disagrees with the actual rendered scene). The 4 immutability
tests in `agent/evals/test_scene_store.py` guard this.

## LangGraph tool wrappers

`agent/store/store_tools.py::create_store_tools(store)` returns six
`langchain_core.tools.BaseTool`s bound to a `SceneStore` via closure:

| tool name        | reads/writes | purpose |
|------------------|--------------|---------|
| `get_manifest`   | r            | "what objects exist?" — uuid->label |
| `get_object`     | r            | full payload of one object |
| `get_objects`    | r            | batch fetch (v1: loops; v2: indexed) |
| `get_zone_map`   | r            | spatial summary for placement |
| `get_camera`     | r            | current camera state |
| `write_to_store` | w            | dispatch on `kind ∈ {brief,object,camera}` |

Tools are constructed per-request so they share a closure scope with the
caller's `SceneStore`. v1 hands these to the asset agent's prompt as
documented capabilities, but the v1 asset code does not actually bind
them to the LLM call (the geometry/material decision uses a single
prompt). v2 will bind them so the agent can query neighbors before
picking a geometry.

## Mocks (v1) and v2 upgrade path

The store carries explicit mocks. Each is tagged with `# MOCK: ...` in
`agent/store/scene_store.py` so future readers can find the v2 work item:

| v1 behavior | v2 behavior |
|-------------|-------------|
| `ZONE_MAP` hardcoded to four contiguous y-ranges (ground/lower/mid/upper) | Compute zones from current scene bounding boxes |
| `get_objects` loops over `get_object` per uuid | True batch fetch from an indexed structure |
| `get_objects_by_stage` filters every object | Maintain a `stage -> [uuid]` index updated on `write_object` |
| `get_zone_map` ignores `self.zone_map` and returns the constant | Layout agent writes computed zones; getter returns those |
| In-memory only; lifetime = one HTTP request | Redis/Postgres persistence keyed by threadId |
| One store per run; no concurrency control | Per-thread store + write locks if v2 adds parallel agent execution |

## Append-only `objectIndex`

The frontend's `objectIndex` (`frontend/serialization/objectIndex.ts`) is
**append-only by plan**: a removed object's uuid stays in `fullIndex` so
the agent retains historical identity. `activeWindow` *does* clean up on
remove (it's a bounded queue tracking recent activity, not history).

This is a deliberate trade-off: it lets a multi-turn agent reference an
object the user just removed ("put a flower where the seed was"), at the
cost of staleness if the agent tries to update the removed uuid (it'll be
a silent no-op via `SceneController.updateObject`).

v2 may add a `tombstones` set so the agent can distinguish "exists and
addressable" from "existed once". Both are useful; the choice here is
v1 simplicity.

## Where this is verified

- `agent/evals/test_scene_store.py` -- 17 tests covering writes, reads,
  manifest shape, zone map, immutability invariants, and the new
  `get_brief` accessor.
- `agent/evals/test_store_tools.py` -- 8 tests covering tool surface,
  proxying, and write-dispatch errors.
