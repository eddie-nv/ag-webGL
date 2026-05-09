# Serialization Strategy

## The problem

The agent needs to reason about the current scene to extend it ("the tomato
plant has a stem; now grow leaves on it"). Naive approaches blow the context
window or leak un-modelable data:

- `scene.toJSON()` includes every geometry's `BufferAttribute` — typed
  `Float32Array` data — and every material's full property bag. A single
  `BoxGeometry` is ~5KB serialized; 30 objects easily reach **50–200KB**
  per round trip.
- Sending the full scene every turn means **O(scene_size × turns)** tokens.
  Demo prompts produce 15+ turns with up to 30 objects.
- Geometry attributes don't fit any LLM's mental model. The agent needs
  semantics ("this is the lower stem"), not vertex buffers.

## The contract: hybrid payload

`frontend/serialization/sceneSerializer.ts` returns a `SerializedScene`:

```typescript
interface SerializedScene {
  activeWindow: SerializedObject[]   // last 3 mutated -- full detail
  fullIndex: Record<string, string>  // uuid -> label, every object
  spatialSummary: ZoneMap            // ground / lower / mid / upper yRanges
  objectCount: number
}
```

Why each piece:

- **`activeWindow`** answers "what just changed?". The agent's last decision
  is the dominant context for the next decision; full detail here is
  cheap (3 × ~300 bytes ≈ 1KB).
- **`fullIndex`** answers "what exists?" without paying for state. Just a
  uuid→label map -- a 30-object scene is ~2KB.
- **`spatialSummary`** answers "where can things go?". The agent uses zones
  (ground / lower / mid / upper) for placement reasoning; the actual y
  coordinates are deterministic given a zone (see `docs/agent-pipeline.md`).

## userData contract

`ObjectFactory.create(payload)` is the **only** way to add a Three.js mesh.
It tags `mesh.userData` with:

```typescript
{
  label: string          // e.g. "tomato_seed"
  geometryType: string   // e.g. "SphereGeometry"
  geometryArgs: number[] // copies of payload.geometryArgs
  stage: string          // e.g. "germination"
  material: { type: string; color: string }
}
```

The serializer reads `userData` and the live transform (`position`,
`rotation`, `scale`, `visible`). It never:

- calls `toJSON` on any object (verified by `vi.spyOn` in the M3 test suite)
- reads `geometry.attributes` (the only exception is an internal NaN-guard
  inside `ObjectFactory`; commented as such)
- embeds texture data — emits a `hasTexture: true` flag instead

## Token cost

Approximate sizes for a 30-object scene with one texture:

| approach          | bytes  | tokens (≈ bytes/4) |
|-------------------|--------|---------------------|
| `scene.toJSON()`  | 60–200 KB | 15k–50k          |
| hybrid payload    | 2–4 KB    | 500–1k           |

The hybrid is **30–50× smaller** and contains the parts the agent reasons
about, none of the parts it doesn't.

## Why not GraphQL / fragments?

CopilotKit's `useCopilotReadable` accepts a value of any shape; the agent
sees it as part of its system context. Adding a query layer would let
agents request specific subsets, but in v1 the activeWindow + fullIndex
pattern already does that statically. v2 may add a `get_object_detail(uuid)`
LangGraph tool that returns a single full object on demand (the
serializer's `objectIndex` already supports this conceptually).

## Mocked pieces (v1)

- **`spatialSummary`** is a hardcoded zone map (`buildZoneMap()` in
  `frontend/serialization/spatialSummary.ts`). v2 will compute zones from
  scene bounding boxes so the agent knows what space is actually occupied.
- **`activeWindow` capacity = 3** is fixed. v2 might tune dynamically.

## Where this is verified

- `frontend/serialization/sceneSerializer.test.ts` -- 10 tests including
  `does not include geometry.attributes`, `never calls toJSON`, and
  `flags hasTexture:true, never embeds data`.
- `frontend/hooks/useSceneReadable.test.ts` -- 6 contract tests on the
  shape fed to `useCopilotReadable`.
