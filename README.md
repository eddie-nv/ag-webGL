# ag-webGL

LangGraph + Three.js demo: type a process at the chat box and a five-agent
pipeline streams scene mutations into a live WebGL canvas via the
AG-UI / CopilotKit event stream.

> "Walk me through a tomato plant's lifecycle." → 13+ objects, lights, camera,
> animation -- composed in ~60 seconds, end to end.

## Architecture

```
                       AG-UI SSE
  ┌──────────────────┐ ◀──────── ┌──────────────────────────────┐
  │  frontend/       │           │  agent/  (Python LangGraph)  │
  │  Next.js 16 +    │  POST     │                              │
  │  Three.js +      │ ────────▶ │  Director ─▶ Layout ─▶       │
  │  CopilotKit 1.57 │ /agui     │     ▶ Asset ─▶ Animation ─▶  │
  │                  │           │       ▶ Lighting             │
  └──────────────────┘           └──────────────────────────────┘
         ▲                              ▲
         │ scene:object_add etc.        │ get_manifest, get_object,
         │ (Custom events)              │ get_zone_map (LangGraph tools)
         ▼                              ▼
  ┌──────────────────┐           ┌──────────────────────┐
  │  SceneController │           │  SceneStore (memory) │
  │  (single mutator │           │  brief, objects,     │
  │   of THREE state)│           │  camera, zone_map    │
  └──────────────────┘           └──────────────────────┘
```

See `docs/` for design rationale on each piece.

## Stack

- **Backend:** Python 3.11+, LangGraph 1.x, FastAPI, AG-UI protocol,
  Anthropic claude-sonnet-4-6 (override via `SCENE_LLM_MODEL`)
- **Frontend:** Next.js 16, React 19, Three.js 0.184, CopilotKit 1.57,
  `@ag-ui/client`, Zod 4
- **Tests:** pytest 9 (backend), vitest 4 (frontend), 80% coverage target

## Prerequisites

- Python 3.11+ (3.14 verified)
- Node 20+ (24 verified)
- An Anthropic API key — set `ANTHROPIC_API_KEY` in `.env` (see `.env.example`)

## Setup

```bash
# Clone the everything-claude-code config source (used by .claude/)
git clone https://github.com/affaan-m/everything-claude-code.git ~/everything-claude-code

# Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Frontend
cd frontend
npm install
cd ..

# Secrets
cp .env.example .env
$EDITOR .env  # paste your ANTHROPIC_API_KEY
```

## Running the demo

Two processes — backend and frontend. Open two terminals.

```bash
# terminal 1 -- backend
.venv/bin/uvicorn agent.main:app --reload --port 8000

# terminal 2 -- frontend
cd frontend && npm run dev
```

Open http://localhost:3000. Type a prompt:

- "Walk me through a tomato plant's lifecycle"
- "Show how a volcano erupts"
- "Demonstrate how a solar system orbits"
- "Show the water cycle"
- "Animate how a bridge is built"

## Tests

```bash
# Backend unit + integration (no API key needed, ~1.5s)
.venv/bin/pytest

# Backend e2e against real Anthropic API (~55s, costs pennies)
.venv/bin/pytest -m e2e

# Frontend
cd frontend && npm test

# Type-check + production build
cd frontend && npx tsc --noEmit && npm run build
```

## Project layout

```
agent/                     # Python LangGraph backend
  main.py                  # FastAPI server (POST /agui SSE)
  graph.py                 # Sequential agent graph
  llm.py                   # AnthropicLLM adapter (LLMClient Protocol)
  agents/
    types.py               # Brief, LLMClient, AgentResult, zone Literals
    placement.py           # Deterministic place_in_zone
    director.py            # Prompt -> Brief
    layout.py              # Brief -> camera_move event
    asset.py               # Brief.objectSummary -> object_add events
    animation.py           # Manifest -> animation_start events
    lighting.py            # Brief.mood -> light_add events (preset)
  store/
    scene_store.py         # In-memory SceneStore (deep-copy boundaries)
    store_tools.py         # 6 LangGraph BaseTool wrappers
  events/
    vocabulary.py          # SCENE_* event-name constants
    scene_events.py        # Typed CustomEvent wrappers
  prompts/                 # Markdown prompt templates
  evals/                   # Pytest evals + fixtures
  tests/                   # Unit tests
frontend/
  app/
    page.tsx               # CopilotKit provider + canvas + chat
    api/copilotkit/route.ts# AG-UI HttpAgent route -> SCENE_AGENT_URL
  components/
    scene/
      SceneCanvas.tsx      # WebGLRenderer + AnimationLoop owner
      SceneController.ts   # Single mutator of THREE.js state
      AnimationLoop.ts     # rAF tick loop
      objects/
        ObjectFactory.ts   # 7-geometry registry, BoxGeometry fallback
        LightFactory.ts    # 3 light types, AmbientLight fallback
    chat/SceneChat.tsx     # CopilotChat header
    hud/StageIndicator.tsx # Stage / agent overlay
  hooks/
    useSceneActions.ts     # routeSceneEvent + useCopilotAction wiring
    useSceneReadable.ts    # buildReadablePayload + useCopilotReadable
    useSceneAgent.ts       # useCoAgent wrapper (currentStage, sendMessage)
  lib/agui/
    customEventTypes.ts    # SCENE_* + discriminated SceneEvent union
  serialization/
    sceneSerializer.ts     # Hybrid payload (no toJSON, no buffers)
    objectIndex.ts         # uuid -> label append-only
    activeWindow.ts        # last-3 mutated UUIDs
    spatialSummary.ts      # Mock zone map (v2: bounding boxes)
shared/schema/
  sceneSchema.py           # Pydantic models for events
  sceneSchema.ts           # Matching Zod schemas
.claude/                   # Claude Code config (rules + agents + commands)
docs/                      # Design rationale (this PR)
```

## Hard rules (preserved across milestones)

- **Never** call `scene.toJSON()` for agent context — see `docs/serialization-strategy.md`
- **Never** create Three.js objects outside `ObjectFactory` / `LightFactory`
- **Never** read `geometry.attributes` from the serializer
- All factory-built objects tag `userData` with `label`, `geometryType`,
  `geometryArgs`, `stage`, `material`
- v1 mocks tagged `// MOCK: replace in v2`
- Tests written before implementation at every milestone

## Plan, decisions, drift

The full milestone plan lives in `PLAN.md`. Each milestone commit
(`milestone(N): ...`) summarizes its drift from the plan and the rationale.
Notable decisions:

- **`shared/schema/sceneSchema.ts`** lives outside `frontend/`; Turbopack
  needs an explicit `next.config.ts` `turbopack.resolveAlias` to pick it up.
- **Asset agent** uses the LLM only for geometry/material; placement is
  deterministic (`place_in_zone`) so the M5 zone evals are verifiable
  without hitting a model.
- **Layout / Animation / Lighting** are deterministic preset-based in v1.
  LLM-driven framing/animation/lighting choices are v2.
- **`objectIndex` is append-only** per the plan, so removed objects stay in
  `fullIndex` for historical agent context. `activeWindow` *does* clean up
  on remove.
- **Default model is `claude-sonnet-4-6`**; override with `SCENE_LLM_MODEL`.

## What's mocked (v1) vs real (v2 backlog)

See `docs/scene-store.md` for the full upgrade path. Highlights:

- `ZONE_MAP` hardcoded; v2 computes from bounding boxes
- `SceneStore.get_objects` loops; v2 batches
- `SceneStore.get_objects_by_stage` filters; v2 indexes
- No persistence; v2 adds Redis or Postgres
- Sequential agent graph; v2 considers parallelism with store locking
- `Animation` agent rotates everything on y; v2 picks per-object animations
