# Event Vocabulary

Six AG-UI `CustomEvent` names mediate every scene mutation. The Python agent
emits them via `agent/events/scene_events.py` wrappers; the React hook
`routeSceneEvent` (`frontend/hooks/useSceneActions.ts`) validates each with
Zod and dispatches to a single `SceneController` method.

Schemas are in **two synchronized files** (one Pydantic, one Zod):

- `shared/schema/sceneSchema.py`
- `shared/schema/sceneSchema.ts`

> Renaming a field requires editing both files and re-running `pytest` and
> `npm test` -- they fail loudly on drift.

## `scene:object_add`

Add a new mesh to the scene. **Required:** `uuid`, `label`, `geometryType`,
`geometryArgs[]`, `material{type, color}`, `position[x,y,z]`, `stage`.
**Optional:** `rotation[x,y,z]`, `scale[x,y,z]`, `visible`.

```json
{
  "uuid": "fd759d88-d370-4519-92b9-d6dec7f8d7ec",
  "label": "tomato_seed",
  "geometryType": "SphereGeometry",
  "geometryArgs": [0.05, 16, 16],
  "material": { "type": "MeshStandardMaterial", "color": "#5b3a1a" },
  "position": [0.0, -0.15, 0.0],
  "stage": "germination"
}
```

Valid `geometryType` (the `ObjectFactory` falls back to `BoxGeometry`
otherwise; see `frontend/components/scene/objects/ObjectFactory.ts`):

`BoxGeometry`, `SphereGeometry`, `CylinderGeometry`, `ConeGeometry`,
`PlaneGeometry`, `TorusGeometry`, `CircleGeometry`.

## `scene:object_update`

Mutate an existing mesh in place. **Required:** `uuid`. **Optional:**
`position`, `rotation`, `scale`, `material`.

```json
{ "uuid": "fd75...", "position": [0.0, 0.05, 0.0] }
```

`material` updates **dispose the old material and replace it** -- not just
a userData write. (M4 fix from code review.)

## `scene:camera_move`

Move the camera. **Required:** `position[x,y,z]`, `target[x,y,z]`.
**Optional:** `fov`.

```json
{ "position": [0, 1.5, 4.5], "target": [0, 0.8, 0], "fov": 50 }
```

`fov` is only applied when the camera is a `PerspectiveCamera`
(`instanceof` guard in `SceneController.moveCamera` -- M4 fix).

## `scene:light_add`

Add a light. **Required:** `uuid`, `lightType`, `color`, `intensity`.
**Optional:** `position[x,y,z]`.

```json
{
  "uuid": "light-1",
  "lightType": "DirectionalLight",
  "color": "#fff8d0",
  "intensity": 1.1,
  "position": [3, 5, 2.5]
}
```

`lightType` is a Zod/Pydantic Literal: `DirectionalLight`, `AmbientLight`,
`PointLight`. The factory falls back to `AmbientLight` for any other value.

## `scene:animation_start`

Start a named animation on an existing object. **Required:** `uuid`,
`animationType`, `duration` (seconds). **Optional:** `axis`, `from`, `to`,
`loop`, `easing`.

```json
{ "uuid": "fd75...", "animationType": "rotate", "duration": 6, "axis": "y", "loop": true }
```

Pydantic stores `from` as `from_` (Python keyword); the `make_animation_start`
wrapper emits `from` on the wire via `by_alias=True`.

V1 only handles `rotate`; other animation types register a no-op tickable.
v2 will pick per-object animations from the lifecycle stages.

## `scene:animation_stop`

Stop a running animation. **Required:** `uuid`.

```json
{ "uuid": "fd75..." }
```

## Why CustomEvent (not tool calls)

AG-UI distinguishes:

- **CustomEvent** — agent → frontend, one-way streaming, no return value.
- **Tool calls** — round-trip, frontend executes a function and returns
  data the agent waits for.

Scene mutations are one-way: the agent decides, the frontend applies. There
is no answer to wait for. CustomEvent matches the data flow exactly and
keeps the agent decoupled from how the frontend actually renders the
mutation. (CopilotKit's `useCopilotAction` is registered as the receiver
for these names — see `frontend/hooks/useSceneActions.ts`.)

## Where this is verified

- `agent/evals/test_event_shapes.py` (9) + `test_scene_events.py` (7) on
  the Python side.
- `frontend/lib/agui/customEventTypes.test.ts` (14) on the TypeScript side.
- `frontend/hooks/useSceneActions.test.ts` (9) for the dispatcher.
- `agent/evals/test_e2e_tomato.py` for live-LLM event-shape conformance.
