# scene-agent-system

Fullstack demo: Python (LangGraph) backend + TypeScript (Next.js) frontend.
Agent pipeline drives a Three.js scene via the AG-UI / CopilotKit event stream.

## Hard Rules

- Never call `scene.toJSON()` for agent context
- Every Three.js object must be created through `ObjectFactory`
- `ObjectFactory` must tag `userData` on every object it creates
- Mock is acceptable — mark every mock with: `// MOCK: replace in v2`
- Tests must be written before implementation at every milestone
- Commit after every milestone, format: `milestone(N): <description>`
- Push after every commit
- Never skip a test to make a milestone pass
- Surface blockers as comments, not silent workarounds

## Project Structure

```
agent/                 # Python LangGraph backend
  events/              # Event vocabulary + typed wrappers
  store/               # In-memory SceneStore + LangGraph tool wrappers
  agents/              # Director, Layout, Asset, Animation, Lighting
  prompts/             # Agent system prompts (.md)
  evals/               # Pytest evals + fixtures
  tests/               # Unit tests
frontend/              # Next.js + Three.js + CopilotKit
  app/                 # Next.js app router
  components/scene/    # SceneCanvas, SceneController, factories, AnimationLoop
  components/chat/     # CopilotChat wrappers
  components/hud/      # StageIndicator
  hooks/               # useSceneActions, useSceneReadable, useSceneAgent
  lib/agui/            # AG-UI custom event types
  serialization/       # objectIndex, activeWindow, spatialSummary, sceneSerializer
shared/schema/         # sceneSchema.ts (Zod) + sceneSchema.py (Pydantic)
.claude/               # Claude Code config (incrementally activated per milestone)
```

## Critical Constraints

- **Never** call `scene.toJSON()` anywhere for agent context
- **Never** read `geometry.attributes` in serializer
- **Never** embed texture data — `hasTexture: true` flag only
- **Never** create Three.js objects outside `ObjectFactory` / `LightFactory`
- Sequential agent execution only in v1 — no parallel graph branches
- In-memory state only — no Redis, no Postgres in v1
- Valid v1 geometry types: `BoxGeometry`, `SphereGeometry`, `CylinderGeometry`,
  `ConeGeometry`, `PlaneGeometry`, `TorusGeometry`, `CircleGeometry`
- Valid v1 light types: `DirectionalLight`, `AmbientLight`, `PointLight`

## Testing Discipline

- TDD enforced from Milestone 1 onward via the `tdd-guide` agent
- Write the failing test first (RED), then implement (GREEN), then refactor
- 80% minimum coverage target
- Backend: `pytest` (unit tests in `agent/tests/`, evals in `agent/evals/`)
- Frontend: `vitest` + `@testing-library/react`
- E2E tests gated by `pytest -m e2e` (requires API key)

## Git Workflow

- Conventional commits with milestone tag for milestone work: `milestone(N): ...`
- Setup/maintenance commits: `chore:`, `docs:`, `fix:`
- See `.claude/rules/ecc/common/git-workflow.md` for full format

## Reference

- Full plan: `PLAN.md` (root)
- ECC rules: `.claude/rules/ecc/`
- Per-language rules activated incrementally: `python/` at M2, `typescript/` at M3
