# Agent Pipeline

Five LangGraph nodes wired sequentially. The graph compiles to a
state machine that takes a `user_prompt`, threads a `SceneStore` and
`LLMClient` through every node, and returns the accumulated event list.

```
START
  │
  ▼
[director]  prompt -> Brief, write_brief()
  │
  ▼
[layout]    Brief -> camera preset, write_camera(), emit scene:camera_move
  │
  ▼
[asset]     Brief.objectSummary -> per item:
  │           LLM(geometry+material), place_in_zone(zone, index),
  │           write_object(), emit scene:object_add
  │
  ▼
[animation] manifest -> per uuid: emit scene:animation_start
  │
  ▼
[lighting]  Brief.mood -> preset -> emit scene:light_add per spec
  │
  ▼
END
```

`agent/graph.py` is intentionally stateless — every node reads/writes
through `SceneStore`. Tests pass a fresh `SceneStore` per run; production
constructs one per request in `agent/main.py`'s `/agui` handler.

## Node responsibilities

### Director (`agent/agents/director.py`)

- Receives the raw user prompt
- Calls the LLM with `agent/prompts/director.md` to produce a `Brief` JSON
- Validates with the Pydantic `Brief` model (Zone Literals, cameraStyle
  Literals, `estimatedObjectCount ∈ [3, 30]`)
- `store.write_brief(brief.model_dump())`
- Emits no events (the brief is internal state)

### Layout (`agent/agents/layout.py`)

- Reads the brief via `store.get_brief()` (deep-copied)
- Re-validates with `Brief.model_validate` so an invalid brief surfaces a
  loud `ValidationError` rather than silently falling back
- Picks a preset from `CAMERA_PRESETS[brief.cameraStyle]` (`wide`,
  `closeup`, `orbit`)
- `store.write_camera(payload)` + emits `scene:camera_move`

V1 is deterministic. v2 lets the LLM choose framing dynamically based on
scene content.

### Asset (`agent/agents/asset.py`)

For each `objectSummary` item:

1. LLM picks `geometryType`, `geometryArgs`, `material` via
   `agent/prompts/asset.md` (validated with `AssetDetails` model)
2. `place_in_zone(zone, zone_map, index)` deterministically picks
   `(x, y, z)` — y at zone midpoint, x/z spread on a 5-col grid
3. Build `ObjectAddPayload`, `store.write_object`, emit `scene:object_add`

The LLM/deterministic split is what makes M5 zone evals verifiable without
a real model: the placement function is pure and the test stub LLM returns
a fixed asset response, so positions are exactly predictable.

**Failure mode:** if the LLM returns malformed JSON for any item (after
`_extract_json` extraction), `AssetDetails.model_validate_json` raises and
the pipeline bails with the partial state already written. v1 trade-off
documented in `agent/agents/asset.py`'s module docstring.

### Animation (`agent/agents/animation.py`)

- Reads manifest (`uuid -> label`)
- Emits one `scene:animation_start` per uuid: `rotate / y / loop=true,
  duration=6s`

V1 rotates everything. v2 picks per-object: stems sway, leaves bob, fruit
ripens. The Brief's `objectSummary[i].stage` informs which animations
should overlap which lifecycle phases.

### Lighting (`agent/agents/lighting.py`)

- Reads `brief.mood`
- Looks up `LIGHT_PRESETS[mood]` (with a `default` fallback)
- Emits one `scene:light_add` per preset entry

Built-in presets:

- `earthy_warm` — Ambient (warm cream) + Directional (soft yellow) +
  Point (peach)
- `cool_clinical` — Ambient (cool blue) + Directional (white)
- `default` — Ambient (white) + Directional (white)

`LightAddPayload.model_validate({"uuid": ..., **spec})` means a preset that
adds a key the schema doesn't recognize fails with a friendly Pydantic
error, not a `TypeError` from `**` unpacking.

## Lazy context hydration

Agents read state through the store, not through the graph state dict.
This means:

- `PipelineState` stays small (just the running event list); it doesn't
  duplicate the brief / camera / objects between nodes.
- A single `SceneStore` is the source of truth, with `deepcopy`-on-read so
  callers can't mutate it sideways.
- LangGraph tools (`agent/store/store_tools.py::create_store_tools`) wrap
  the store's read API for any LLM-driven step that needs to query
  existing objects. The Asset prompt references `get_zone_map`,
  `get_manifest`, `get_object` -- in v2 the asset agent will actually
  bind these tools to its model call so it can look at neighbors before
  picking a geometry.

## LLM client

`agent.llm.AnthropicLLM` is the default production client (claude-sonnet-4-6).
The `LLMClient` Protocol (`agent/agents/types.py`) is a single method:

```python
class LLMClient(Protocol):
    def invoke(self, prompt: str) -> str: ...
```

Tests pass `StubLLM` / `CycleStubLLM` -- deterministic, free, no API calls.

`AnthropicLLM.invoke` post-processes the model response with `_extract_json`,
which:

1. Tries `\`\`\`json ... \`\`\`` fenced extraction first
2. Falls back to "first `{` to last `}`" / "first `[` to last `]`"
3. Returns the original text if neither matches (Pydantic raises a clearer
   error than a regex would)

This was the M8 fix that turned the asset agent from "raises ValidationError
on the third call" to "succeeds on every prompt in TEST_PROMPTS".

## Where this is verified

- 24 unit tests across `test_director.py`, `test_layout.py`, `test_asset.py`
  (within `test_zone_placement.py`), `test_animation.py`, `test_lighting.py`,
  `test_graph.py` -- all with stub LLMs
- 3 e2e tests in `test_e2e_tomato.py` against `claude-sonnet-4-6`
- 7 placement tests verifying `place_in_zone` invariants
