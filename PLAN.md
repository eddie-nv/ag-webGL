# scene-agent-system V1 — Claude Code Plan

## Before You Start: Clone everything-claude-code

Before opening Claude Code on this repo, clone the config source:

```bash
git clone https://github.com/affaan-m/everything-claude-code.git ~/everything-claude-code
```

Copy specific files from it at the milestones marked below. Do not run the
full installer. Do not copy everything. Each config activates at the point
where it starts earning its keep.

---

## Rules for Claude Code

- Commit after every milestone. Format: `milestone(N): <description>`
- Push after every commit
- Never skip a test to make a milestone pass
- Surface blockers as comments, not silent workarounds
- Never call `scene.toJSON()` for agent context
- Every object created by `ObjectFactory` must tag `userData`
- Mark every mock with `// MOCK: replace in v2`

---

## .claude/ Built Incrementally

```
.claude/
├── CLAUDE.md                    # Milestone 0
├── rules/ecc/
│   ├── common/                  # Milestone 0
│   │   ├── git-workflow.md
│   │   ├── testing.md
│   │   └── coding-style.md
│   ├── python/                  # Milestone 2
│   └── typescript/              # Milestone 3
├── agents/
│   ├── tdd-guide.md             # Milestone 1
│   ├── code-reviewer.md         # Milestone 4
│   ├── planner.md               # Milestone 5
│   └── python-reviewer.md       # Milestone 5
└── commands/
    ├── plan.md                  # Milestone 6
    └── code-review.md           # Milestone 6
```

---

## Config Selection Rationale

**Copied at Milestone 0**
- `rules/common/git-workflow.md` — enforces `milestone(N):` commit format from commit 1
- `rules/common/testing.md` — TDD and 80% coverage before any code is written
- `rules/common/coding-style.md` — language-agnostic style across Python and TypeScript
- `CLAUDE.md` — top-level session instructions, paste in hard rules from this plan

**Copied at Milestone 2**
- `rules/python/` — type hints, pytest conventions, import order. Pointless before Python code exists.

**Copied at Milestone 3**
- `rules/typescript/` — strict mode, no `any`, naming. Pointless before TypeScript code exists.

**Copied at Milestone 1**
- `agents/tdd-guide.md` — RED→GREEN→REFACTOR enforcement. First real tests are written here.

**Copied at Milestone 4**
- `agents/code-reviewer.md` — first complex implementation. Review before moving on.

**Copied at Milestone 5**
- `agents/planner.md` — LangGraph graph wiring is the most complex planning task. Use it.
- `agents/python-reviewer.md` — bulk of Python complexity is in the agent pipeline.

**Copied at Milestone 6**
- `commands/plan.md`, `commands/code-review.md` — slash shortcuts useful during integration work.

**Deliberately Not Copied**
- `hooks/` — memory-persistence and session hooks add global behavior that breaks test isolation
- `skills/continuous-learning*/` — v2 concern
- `skills/eval-harness/` — we write our own evals, not a general framework
- `agents/architect.md` — architecture is already decided in this plan
- `agents/security-reviewer.md` — no auth surface in a demo with in-memory state
- `rules/golang/`, `rules/swift/`, `rules/php/` — not in our stack

---

## Milestone 0 — Repo Init, Tooling, Base Config

**Goal:** Empty repo with working test runners. Claude Code configured with
foundational rules before any code is written.

### Activate Now

```bash
mkdir -p .claude/rules/ecc/common

cp ~/everything-claude-code/rules/common/git-workflow.md  .claude/rules/ecc/common/
cp ~/everything-claude-code/rules/common/testing.md       .claude/rules/ecc/common/
cp ~/everything-claude-code/rules/common/coding-style.md  .claude/rules/ecc/common/
cp ~/everything-claude-code/examples/CLAUDE.md            .claude/CLAUDE.md
```

Edit `.claude/CLAUDE.md` — add at the top:

```markdown
# scene-agent-system

Fullstack demo: Python (LangGraph) backend + TypeScript (Next.js) frontend.
Agent pipeline drives a Three.js scene via AG-UI / CopilotKit event stream.

## Hard Rules
- Never call scene.toJSON() for agent context
- Every Three.js object must be created through ObjectFactory
- ObjectFactory must tag userData on every object it creates
- Mock is acceptable — mark every mock with: // MOCK: replace in v2
- Tests must be written before implementation at every milestone
```

### Tasks

**Backend**
- Init Python project with `pyproject.toml`
- Install: `langgraph`, `fastapi`, `uvicorn`, `ag-ui-protocol`, `pytest`
- Create `agent/` package with empty `__init__.py` files
- Configure `pytest` in `pyproject.toml`
- Smoke test: `assert 1 == 1`

**Frontend**
- Init Next.js app with TypeScript in `frontend/`
- Install: `three`, `@copilotkit/react-core`, `@copilotkit/react-ui`,
  `@copilotkit/runtime`, `@ag-ui/client`, `vitest`, `@testing-library/react`
- Configure `vitest` in `vite.config.ts`
- Smoke test: `expect(true).toBe(true)`

**Shared**
- Create `shared/schema/` with empty `sceneSchema.ts` and `sceneSchema.py`

### Commit
```
milestone(0): repo init, test runners green, base claude config active
```

---

## Milestone 1 — Event Vocabulary + TDD Agent

**Goal:** Both sides agree on the contract. TDD agent active so all subsequent
tests are written RED before any implementation.

### Activate Now

```bash
mkdir -p .claude/agents
cp ~/everything-claude-code/agents/tdd-guide.md .claude/agents/
```

The TDD agent enforces test-first from this point forward. Every file
written after this milestone starts with a failing test.

### Tasks

**`agent/events/vocabulary.py`**

```python
SCENE_OBJECT_ADD    = "scene:object_add"
# required: uuid, label, geometryType, geometryArgs[], material{type,color},
#           position[x,y,z], stage
# optional: rotation[x,y,z], scale[x,y,z], visible

SCENE_OBJECT_UPDATE = "scene:object_update"
# required: uuid
# optional: position, rotation, scale, material

SCENE_CAMERA_MOVE   = "scene:camera_move"
# required: position[x,y,z], target[x,y,z]
# optional: fov

SCENE_LIGHT_ADD     = "scene:light_add"
# required: uuid, lightType (DirectionalLight|AmbientLight|PointLight),
#           color, intensity
# optional: position[x,y,z]

SCENE_ANIMATION_START = "scene:animation_start"
# required: uuid, animationType, duration
# optional: axis, from, to, loop, easing

SCENE_ANIMATION_STOP  = "scene:animation_stop"
# required: uuid
```

**`agent/events/scene_events.py`** — typed CustomEvent wrappers
**`frontend/lib/agui/customEventTypes.ts`** — TypeScript interfaces mirroring vocabulary exactly
**`shared/schema/sceneSchema.ts`** — Zod schemas per payload
**`shared/schema/sceneSchema.py`** — Pydantic models per payload

### Tests (RED first — tdd-guide agent enforces this)

**`agent/evals/test_event_shapes.py`**
```python
def test_object_add_requires_uuid()
def test_object_add_requires_geometry_type()
def test_object_add_valid_payload_passes()
def test_camera_move_requires_position_and_target()
def test_light_add_valid_types_only()
def test_animation_start_requires_duration()
```

**`frontend/lib/agui/customEventTypes.test.ts`**
```ts
test('object_add payload matches schema')
test('missing uuid fails validation')
test('camera_move missing target fails validation')
```

### Commit
```
milestone(1): event vocabulary defined, validated both sides, tdd-guide active
```

---

## Milestone 2 — Scene Store + Python Rules

**Goal:** Agents have a queryable in-memory store. Python rules active.

### Activate Now

```bash
mkdir -p .claude/rules/ecc/python
cp -r ~/everything-claude-code/rules/python/ .claude/rules/ecc/python/
```

Type hints and pytest conventions now enforced on all Python files.

### Tasks

**`agent/store/scene_store.py`**

```python
class SceneStore:
    def __init__(self):
        self.brief: dict = {}
        self.objects: dict[str, dict] = {}
        self.camera: dict = {}
        self.zone_map: dict = {}     # MOCK: hardcoded zones
        self.current_stage: str = ""
        self.stages_completed: list[str] = []
        self.stages_remaining: list[str] = []

    def write_brief(self, brief: dict): ...
    def write_object(self, uuid: str, payload: dict): ...
    def write_camera(self, payload: dict): ...
    def get_manifest(self) -> dict[str, str]: ...   # uuid → label only
    def get_object(self, uuid: str) -> dict | None: ...
    def get_objects(self, uuids: list[str]) -> list[dict]: ...  # MOCK: loop
    def get_zone_map(self) -> dict: ...             # MOCK: hardcoded
    def get_camera(self) -> dict: ...
    def get_objects_by_stage(self, stage: str) -> list[dict]: ...  # MOCK: filter

# MOCK: replace in v2 with bounding box computation
ZONE_MAP = {
    "ground": {"yRange": [-0.3, 0.0]},
    "lower":  {"yRange": [0.0, 0.6]},
    "mid":    {"yRange": [0.6, 1.2]},
    "upper":  {"yRange": [1.2, 2.0]}
}
```

**`agent/store/store_tools.py`**
LangGraph tool wrappers: `get_manifest`, `get_object`, `get_objects`,
`get_zone_map`, `get_camera`, `write_to_store`

### Tests (RED first)

**`agent/evals/test_scene_store.py`**
```python
def test_write_and_get_object()
def test_get_manifest_returns_labels_only()
def test_get_object_returns_none_for_missing()
def test_get_objects_batch_returns_all()
def test_get_objects_by_stage_filters_correctly()
def test_zone_map_returns_four_zones()
def test_write_brief_stores_brief()
def test_get_camera_returns_camera_state()
```

### Commit
```
milestone(2): scene store implemented, all queries tested, python rules active
```

---

## Milestone 3 — Serializer + TypeScript Rules

**Goal:** Purpose-built scene serializer. TypeScript rules active.
Reads userData only. Never touches geometry buffers.

### Activate Now

```bash
mkdir -p .claude/rules/ecc/typescript
cp -r ~/everything-claude-code/rules/typescript/ .claude/rules/ecc/typescript/
```

Strict mode and no `any` now enforced on all TypeScript files.

### Tasks

**`frontend/serialization/objectIndex.ts`**
Append-only uuid → label map. Methods: `add()`, `getAll()`, `size()`.

**`frontend/serialization/activeWindow.ts`**
Tracks last 3 mutated UUIDs. `push()` drops oldest. N=3 fixed for v1.

**`frontend/serialization/spatialSummary.ts`**
```ts
// MOCK: replace in v2 with bounding box computation
export function buildZoneMap(): ZoneMap {
  return {
    ground: { yRange: [-0.3, 0.0] },
    lower:  { yRange: [0.0, 0.6] },
    mid:    { yRange: [0.6, 1.2] },
    upper:  { yRange: [1.2, 2.0] }
  }
}
```

**`frontend/serialization/sceneSerializer.ts`**
- Walks `scene.traverse()`, reads `userData` only
- Never touches `geometry.attributes`
- Never calls `scene.toJSON()`
- Textures: `hasTexture: true` flag only, never embed data
- Returns three-part hybrid payload

### Tests (RED first)

**`frontend/serialization/sceneSerializer.test.ts`**
```ts
test('serializes object into activeWindow when uuid is in window')
test('objects not in activeWindow appear in index only')
test('does not include geometry.attributes in output')
test('never calls toJSON on any object')
test('handles empty scene without throwing')
test('objectCount matches traversal count')
test('extracts position, rotation, scale as plain arrays')
test('flags hasTexture:true, never embeds data')

// ObjectIndex
test('add and getAll returns correct map')
test('size increments on each add')

// ActiveWindow
test('push drops oldest when at capacity')
test('capacity is capped at 3')
```

### Commit
```
milestone(3): serializer tested, no geometry buffers in output, ts rules active
```

---

## Milestone 4 — ObjectFactory, SceneController + Code Reviewer

**Goal:** All Three.js mutations go through these two modules.
Code reviewer activated — run it before committing this milestone.

### Activate Now

```bash
cp ~/everything-claude-code/agents/code-reviewer.md .claude/agents/
```

After tests pass, before committing:
```
@code-reviewer review ObjectFactory.ts, LightFactory.ts, SceneController.ts
for correctness, edge cases, and userData tagging completeness
```

### Tasks

**`frontend/components/scene/objects/ObjectFactory.ts`**

```ts
// CRITICAL: tags userData on every created object
// try/catch fallback to BoxGeometry for unknown geometry type names
// Tags: userData.label, userData.geometryType, userData.geometryArgs, userData.stage
// Valid v1 geometry types:
// BoxGeometry, SphereGeometry, CylinderGeometry, ConeGeometry,
// PlaneGeometry, TorusGeometry, CircleGeometry
```

**`frontend/components/scene/objects/LightFactory.ts`**
Supports `DirectionalLight`, `AmbientLight`, `PointLight`.
Falls back to `AmbientLight` for unknown types.

**`frontend/components/scene/SceneController.ts`**
```ts
class SceneController {
  addObject(payload): void      // ObjectFactory → scene.add → activeWindow.push
  updateObject(uuid, updates): void
  removeObject(uuid): void
  moveCamera(payload, camera): void
  addLight(payload): void       // LightFactory → scene.add
  startAnimation(payload): void // AnimationLoop.register
  stopAnimation(uuid): void     // AnimationLoop.unregister
}
```

### Tests (RED first)

**`frontend/components/scene/objects/ObjectFactory.test.ts`**
```ts
test('creates mesh with correct geometry type')
test('tags userData.label')
test('tags userData.geometryType')
test('tags userData.geometryArgs')
test('tags userData.stage')
test('falls back to BoxGeometry for unknown type')
test('fallback logs a warning')
test('sets position from payload')
test('sets uuid from payload')
```

**`frontend/components/scene/SceneController.test.ts`**
```ts
test('addObject adds mesh to scene')
test('addObject pushes uuid to activeWindow')
test('updateObject changes position')
test('updateObject pushes uuid to activeWindow')
test('removeObject removes from scene')
test('addLight adds light to scene')
test('moveCamera updates position and target')
```

### Commit (after code review passes)
```
milestone(4): ObjectFactory and SceneController tested, code review passed
```

---

## Milestone 5 — Agent Pipeline + Planner + Python Reviewer

**Goal:** Five LangGraph agents wired sequentially. Tested with mocked LLM.

### Activate Now

```bash
cp ~/everything-claude-code/agents/planner.md         .claude/agents/
cp ~/everything-claude-code/agents/python-reviewer.md .claude/agents/
```

Use planner before writing `graph.py`:
```
@planner design the LangGraph sequential graph wiring Director → Layout
→ Asset → Animation → Lighting. Each node takes SceneStore as input.
Output node function signatures before implementation.
```

Use python-reviewer after each agent file is complete.

### Tasks

**`agent/prompts/director.md`** — defines the brief output schema:
```json
{
  "subject": "string",
  "stages": ["string"],
  "mood": "string",
  "cameraStyle": "wide|closeup|orbit",
  "estimatedObjectCount": "number",
  "objectSummary": [{"label":"string","zone":"string","stage":"string"}]
}
```

**`agent/prompts/asset.md`** — must explain:
- call `get_zone_map` before placing any object
- call `get_manifest` to check what exists
- call `get_object(uuid)` for relative positioning
- valid geometry types list (7 types only)

**`agent/agents/director.py`** — parses prompt, writes brief to store
**`agent/agents/layout.py`** — reads brief, writes zone_map + camera, emits `scene:camera_move`
**`agent/agents/asset.py`** — reads brief + zones, queries store, emits `scene:object_add`
**`agent/agents/animation.py`** — reads manifest, queries positions, emits `scene:animation_start`
**`agent/agents/lighting.py`** — reads mood + zones, queries camera, emits `scene:light_add`
**`agent/graph.py`** — sequential graph, no parallel execution in v1

**`agent/evals/fixtures/prompts.py`**
```python
TEST_PROMPTS = [
    "Walk me through a tomato plant's lifecycle",
    "Show how a volcano erupts",
    "Demonstrate how a solar system orbits",
    "Show the water cycle",
    "Animate how a bridge is built",
]
```

**`agent/evals/fixtures/expected_events.py`**
```python
TOMATO_EXPECTED = {
    "scene:camera_move":     {"min": 1},
    "scene:object_add":      {"min": 3, "max": 30},
    "scene:light_add":       {"min": 2},
    "scene:animation_start": {"min": 2},
}
```

### Tests (RED first — mocked LLM, no real API calls)

**`agent/evals/test_zone_placement.py`**
```python
def test_position_in_declared_zone()
def test_position_not_in_wrong_zone()
def test_asset_agent_emits_object_add_per_brief_item()
def test_asset_agent_positions_match_declared_zones()
```

After tests pass:
```
@python-reviewer review agent/agents/ for type safety, error handling,
and correct store query patterns
```

### Commit
```
milestone(5): agent pipeline sequential, zone evals green, agents reviewed
```

---

## Milestone 6 — CopilotKit Integration + Slash Commands

**Goal:** Frontend hooks wired. Events from agent stream reach SceneController.

### Activate Now

```bash
mkdir -p .claude/commands
cp ~/everything-claude-code/commands/plan.md        .claude/commands/
cp ~/everything-claude-code/commands/code-review.md .claude/commands/
```

Use `/plan` to outline hook wiring before implementing.
Use `/code-review` on completed hooks before committing.

### Tasks

**`frontend/hooks/useSceneActions.ts`**
One `useCopilotAction` per vocabulary event. Each routes to SceneController.

**`frontend/hooks/useSceneReadable.ts`**
Calls `sceneSerializer` on every run. Feeds hybrid payload via `useCopilotReadable`.

**`frontend/hooks/useSceneAgent.ts`**
`useAgent` wrapper. Exposes `currentStage`, `activeAgentName`, `sendMessage`.

**`frontend/app/api/copilotkit/route.ts`**
```ts
const sceneAgent = new HttpAgent({ url: "http://localhost:8000/agui" })
const runtime = new CopilotRuntime({ agents: { sceneAgent } })
export const POST = copilotRuntimeNextJSAppRouterEndpoint({ runtime, req })
```

### Tests (RED first)

**`frontend/hooks/useSceneActions.test.ts`**
```ts
test('scene:object_add calls controller.addObject')
test('scene:camera_move calls controller.moveCamera')
test('scene:light_add calls controller.addLight')
test('scene:animation_start calls controller.startAnimation')
test('scene:object_update calls controller.updateObject with uuid')
test('malformed payload does not throw unhandled error')
```

**`frontend/hooks/useSceneReadable.test.ts`**
```ts
test('readable payload contains activeWindow array')
test('readable payload contains fullIndex')
test('readable payload does not contain Float32Array data')
test('readable payload contains spatialSummary with four zones')
```

After tests pass:
```
/code-review
```

### Commit
```
milestone(6): copilotkit hooks wired, tested with mocked stream, slash commands active
```

---

## Milestone 7 — Three.js Canvas and Animation Loop

**Goal:** Scene renders in browser. Animation loop running. Objects appear on screen.

### Tasks

**`frontend/components/scene/AnimationLoop.ts`**
```ts
interface Tickable { uuid: string; tick(delta: number): void }
class AnimationLoop {
  register(obj: Tickable): void
  unregister(uuid: string): void
  start(renderer, scene, camera): void
  stop(): void
}
```

**`frontend/components/scene/SceneCanvas.tsx`**
- Creates Scene, PerspectiveCamera, WebGLRenderer
- Starts AnimationLoop
- Passes sceneRef to SceneController
- Registers `useSceneActions` and `useSceneReadable`
- Cleanup: stops loop on unmount, disposes renderer

**`frontend/components/chat/SceneChat.tsx`** — `<CopilotChat>` with active agent name
**`frontend/components/hud/StageIndicator.tsx`** — stage progress display

### Tests (RED first)

**`frontend/components/scene/AnimationLoop.test.ts`**
```ts
test('register adds object to updatables')
test('unregister removes object by uuid')
test('tick is called on all registered objects')
test('tick receives delta time argument')
test('registering same uuid twice does not duplicate')
```

**`frontend/components/scene/SceneCanvas.test.tsx`**
```tsx
// Mock THREE.WebGLRenderer to avoid canvas in test env
test('mounts without throwing')
test('calls renderer.dispose on unmount')
test('AnimationLoop.stop called on unmount')
```

### Commit
```
milestone(7): canvas renders, animation loop running, cleanup verified
```

---

## Milestone 8 — End-to-End Integration Test

**Goal:** Full pipeline on real prompt with real LLM.

### Tasks

**`agent/evals/test_e2e_tomato.py`**
```python
# pytest.mark.e2e — skipped in CI unless flag set
# Requires API key in env

@pytest.mark.e2e
def test_tomato_lifecycle_emits_minimum_events():
    events = run_pipeline("Walk me through a tomato plant's lifecycle")
    assert len([e for e in events if e.name == "scene:object_add"]) >= 3
    assert len([e for e in events if e.name == "scene:light_add"]) >= 2
    assert len([e for e in events if e.name == "scene:camera_move"]) >= 1

@pytest.mark.e2e
def test_tomato_lifecycle_all_objects_have_valid_geometry():
    events = run_pipeline("Walk me through a tomato plant's lifecycle")
    valid_types = {
        "BoxGeometry","SphereGeometry","CylinderGeometry",
        "ConeGeometry","PlaneGeometry","TorusGeometry","CircleGeometry"
    }
    for e in [e for e in events if e.name == "scene:object_add"]:
        assert e.value["geometryType"] in valid_types

@pytest.mark.e2e
def test_tomato_lifecycle_positions_in_valid_zones():
    events = run_pipeline("Walk me through a tomato plant's lifecycle")
    for e in [e for e in events if e.name == "scene:object_add"]:
        y = e.value["position"][1]
        assert -0.3 <= y <= 2.0
```

**Browser smoke test checklist (manual)**
```
[ ] Chat streams text progressively as agent runs
[ ] Objects appear in canvas as scene:object_add events arrive
[ ] Camera moves on scene:camera_move events
[ ] Lights illuminate scene on scene:light_add events
[ ] StageIndicator updates as stages progress
[ ] No unhandled console errors
[ ] Typing "Show how a volcano erupts" produces a different scene
```

### Commit
```
milestone(8): e2e passing on tomato prompt, browser smoke checklist done
```

---

## Milestone 9 — Docs and Demo Cleanup

**Goal:** Anyone can clone and run. Docs explain every non-obvious decision.

### Tasks

**`docs/serialization-strategy.md`** — why not toJSON, token cost table, userData contract
**`docs/event-vocabulary.md`** — every event, required/optional fields, example payloads
**`docs/agent-pipeline.md`** — sequential order, lazy context hydration pattern
**`docs/scene-store.md`** — store API, what is mocked, v2 upgrade path

**`README.md`**
```
Prerequisites: Python 3.11+, Node 20+, API key (Anthropic or OpenAI)

# Backend
cd agent && pip install -e .
pytest                    # unit tests
pytest -m e2e             # e2e tests (needs API key)
uvicorn main:app --reload

# Frontend
cd frontend && npm install
npm test
npm run dev

Open http://localhost:3000
Type any process to animate: "show how a volcano erupts"
```

### Commit
```
milestone(9): docs complete, demo ready, README verified on clean clone
```

---

## Config Activation Summary

| Milestone | What Gets Activated | Why Then |
|---|---|---|
| 0 | `rules/common/*`, `CLAUDE.md` | Before any code — sets commit format and test discipline |
| 1 | `agents/tdd-guide.md` | First real tests — enforces RED→GREEN→REFACTOR |
| 2 | `rules/python/` | Python code begins |
| 3 | `rules/typescript/` | TypeScript code begins |
| 4 | `agents/code-reviewer.md` | First complex implementation — review before moving on |
| 5 | `agents/planner.md`, `agents/python-reviewer.md` | Most complex milestone |
| 6 | `commands/plan.md`, `commands/code-review.md` | Integration work — shortcuts useful here |

---

## What Claude Code Should Not Do

- Do not implement `PostEffectFactory` — deferred to v2
- Do not implement `spatialSummary` bounding box computation — use the mock
- Do not add session persistence — in-memory only
- Do not add parallel agent execution — sequential graph only
- Do not use `scene.toJSON()` anywhere for agent context
- Do not create objects outside `ObjectFactory`
- Do not skip tests to hit a milestone

## V2 Backlog (Do Not Implement Now)

- `spatialSummary.ts` real bounding box computation
- `getObjects()` true batch query
- `PostEffectFactory` and compositor agent
- Touchup agent
- Session persistence (Redis or Postgres)
- Parallel agent execution with store locking
- `shared/schema` codegen between Python and TypeScript
- External model loading (glTF, FBX)
- `SkinnedMesh` and bone hierarchy support
- `InstancedMesh` handling in serializer
