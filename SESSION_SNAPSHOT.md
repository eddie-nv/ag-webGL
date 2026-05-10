# Session Snapshot — 2026-05-09

A pickup-where-we-left-off doc for the next session.

## TL;DR — current state

- **Repo:** https://github.com/eddie-nv/ag-webGL
- **Branch:** `main`, all work committed and pushed.
- **Latest commit:** `83a65bc feat(controls): inline control-panel chat bubbles`
- **Tests:** 103 pytest (3 e2e deselected, run with `pytest -m e2e`),
  103 vitest, `tsc --noEmit` clean, `next build` succeeds.
- **Live demo target:** EC2 `t4g.large` (Graviton arm64, 8 GB, 20 GB
  gp3), provisioned via `scripts/aws-ec2.sh` and bootstrapped via
  `scripts/ec2-bootstrap.sh`. SSH tunnel forwards `localhost:3000` and
  `localhost:8000` from the EC2 to the local Mac.
- **LLM:** `claude-sonnet-4-6` (override via `SCENE_LLM_MODEL`). API key
  in `.env` at the project root (gitignored).

## Architecture (current — post-CopilotKit pivot)

```
Browser                Next.js /api/agui          Python /agui                Anthropic
   │                          │                        │                          │
   │ POST {prompt,            │                        │                          │
   │       sceneSnapshot}     │                        │                          │
   │─────────────────────────▶│                        │                          │
   │                          │  POST {…}              │                          │
   │                          │───────────────────────▶│                          │
   │                          │                        │  hydrate store from      │
   │                          │                        │  snapshot, then for each │
   │                          │                        │  agent in sequence:      │
   │                          │                        │    yield narration       │
   │                          │                        │    asyncio.to_thread(    │
   │                          │                        │      run_agent, …) ◀─────┤  blocks 5–10s
   │                          │                        │    yield events          │
   │                          │                        │  Controls (last):        │
   │                          │                        │    yield panel event     │
   │                          │                        │  yield RunFinished       │
   │ ◀──────── SSE stream ────────────────────────────┤                          │
   │                                                                               │
   │ for each event:                                                               │
   │   TEXT_MESSAGE_*  → append to chat bubble keyed by messageId                  │
   │   CUSTOM scene:*  → routeSceneEvent → SceneController                         │
   │   CUSTOM scene:control_panel → render <ControlPanel> bubble inline            │
```

CopilotKit is **removed from the client**. We use a custom chat that
parses AG-UI SSE directly. The Next.js route at `/api/agui` is a thin
proxy to the FastAPI backend.

## Pipeline (current — 6 stages)

1. **Director** — LLM call. Reads prompt + current scene snapshot,
   produces a `Brief` with additions / updates / removals / cameraAction
   / animate / controlPanel.
2. **Layout** — deterministic. Emits `scene:camera_move` only if the
   brief has additions (modify-only prompts preserve framing).
3. **Asset** — LLM call **per addition**. Walks removals → updates →
   additions, emitting `scene:object_remove` / `scene:object_update` /
   `scene:object_add` plus per-object animation_stop when
   `BriefUpdate.stopAnimation` is set. Uses `Placer` for anchor-aware
   spatial composition. Skips items with hallucinated uuids and yields
   a chat-visible warning.
4. **Animation** — deterministic. Emits camera spin start/stop based on
   `cameraAction.spin` + `cameraAction.stopSpin`, and per-object rotate
   when `brief.animate` AND multi-stage.
5. **Lighting** — deterministic. Emits 2–3 lights from a mood preset.
6. **Controls** — deterministic. Emits `scene:control_panel` if the
   brief has one. No-op otherwise.

## What was built this session

In rough order. Every item is committed and pushed.

| Topic | Outcome |
|---|---|
| **EC2 provisioning** | `scripts/aws-ec2.sh` (launch / status / ssh / tunnel / stop / start / terminate) + `scripts/ec2-bootstrap.sh` (apt deps, swap, Node 20, venv, npm install). Region/instance-type from env. |
| **`lib/` gitignore bug** | Discovered `frontend/lib/agui/customEventTypes.{ts,test.ts}` was silently untracked across all milestones. macOS case-insensitive FS hid it locally. Fixed by anchoring `/lib/` and `/lib64/` to repo root. |
| **CopilotKit pivot** | First EC2 run: backend emitted 48 events, browser saw zero `[scene] event in:` lines. Diagnosed: `useCopilotAction` is for tool calls, doesn't dispatch AG-UI CustomEvents. Removed `@copilotkit/react-*` from the client; built custom chat + `/api/agui` proxy. |
| **Phase 1 — true streaming** | Bubbles arrived in clumps. Two fixes: (a) yield narration **before** each agent runs, not after; (b) wrap blocking `model.invoke` in `asyncio.to_thread` so the asyncio loop keeps flushing; (c) `dynamic = 'force-dynamic'` on the proxy route. |
| **Phase 2+3 — continuity + remove/spin** | "remove the cube" / "move it up" / "spin the camera" all worked end-to-end. Frontend POSTs `sceneSnapshot` per prompt; backend hydrates a `SceneStore`; Director sees uuids; Brief grew `updates / removals / cameraAction`. Camera animation reuses `scene:animation_start` with sentinel `uuid="camera"`. |
| **Phase 4 — curated three.js reference** | ~100 lines of geometry / material / lighting reference inlined into `agent/prompts/asset.md`. Skipped the `.claude/skills/` install per user choice. |
| **v2 backlog** | `docs/v2-backlog.md` with Phases 5–8 + smaller fixes, ordered by effort × impact. |
| **Phase 5 — stop animation + hallucinated-uuid feedback** | `cameraAction.stopSpin`, `BriefUpdate.stopAnimation`. Asset skips removals/updates with unknown uuids and surfaces a chat warning. Frontend `routeSceneEvent` warns on unknown uuids in DevTools. |
| **Composition fix** | "make a flower" was scattering parts across the grid. Added `AnchorSpec` + `Placer` class with three modes: anchor-aware (geometry-aware clearance), centered stacking (single-subject ≤6 items), grid (multi-subject fallback). Composition root detection auto-centers items referenced by others. |
| **Control panels** | New `scene:control_panel` event. Director can include a `controlPanel` in the Brief; new `Controls` agent emits it. Frontend renders inline `<ControlPanel>` chat bubble with buttons + toggles. Both dispatch through the existing `routeSceneEvent` path. |

## What works (verified)

- Pytest 103 / vitest 103 / tsc clean / next build clean — all CI-grade.
- Backend SSE smoke test: `curl POST /agui` produces RunStarted →
  TEXT_MESSAGE → CUSTOM ×N → RunFinished in real time.
- E2e (`pytest -m e2e`): tomato lifecycle prompt against
  `claude-sonnet-4-6` produces ≥3 object_add, ≥2 light_add, valid
  geometry types, positions inside zone bounds.
- User confirmed live: "make a blue cube" produces a single static
  cube; chat narrates each agent in real time; `[scene] event in:`
  lines flow per-event.

## What works (built but not yet verified by user)

- Phase 5: "stop the camera" / "stop spinning the cube". Tests cover
  the wire path; user hasn't run the full prompt sequence yet.
- Composition fix: "make a flower" / "make a robot" should now
  compose. Tested by 15 unit tests on `Placer`; live verification
  pending.
- Control panels: "give me controls" → inline panel with buttons +
  toggles. Schema + component fully unit-tested; live verification
  pending.

## What didn't work the first time (pitfalls to remember)

| Failure | Root cause | Fix |
|---|---|---|
| `customEventTypes.ts` missing on EC2 build | `lib/` in gitignore matched `frontend/lib/` | Anchor with leading slash |
| Backend emitted N events, frontend saw 0 | CopilotKit's `useCopilotAction` is tool-only | Bypass CopilotKit; consume SSE directly |
| Bubbles all arrived at once after 60s | Sync LLM blocked asyncio loop; narration yielded AFTER work | `asyncio.to_thread` + narrate-before-run |
| Next.js proxy buffered the upstream body | App Router defaults to caching | `export const dynamic = 'force-dynamic'` + `runtime = 'nodejs'` |
| `useAgent` not exported from `@copilotkit/react-core` | It's in a sub-file, not the public surface | Used `useCoAgent` instead (during the CopilotKit era) |
| Schema changes broke fixture briefs across many tests | Each phase grew the Brief; tests had inline literals | Add fields with defaults, never as required, so old fixtures still validate |
| `outputFileTracingRoot` needed for `@shared/*` imports | Turbopack rejects parent-of-project imports without explicit allowance | `next.config.ts` `turbopack.resolveAlias` |
| Pydantic dumps `Vec3` as Python tuple | TS expects array | Round-trips through JSON → array; tests assert via `tuple(value)` or list comparison |
| Anchor-based placement | LLM might forget to declare anchors | Added composition-root detection + small-brief stacking heuristic so single-subject prompts stack even without anchors |

## Hot files (where to look for what)

| Concern | File |
|---|---|
| Brief schema (the contract) | `agent/agents/types.py` |
| Director prompt (most behavior tuning happens here) | `agent/prompts/director.md` |
| Asset prompt (geometry/material taste) | `agent/prompts/asset.md` |
| SSE stream construction | `agent/main.py:_stream_pipeline` |
| Spatial composition (anchors / stacking / grid) | `agent/agents/placement.py` |
| Per-item asset stage (remove / update / add) | `agent/agents/asset.py:iter_asset_items` |
| All AG-UI custom event names + payload schemas | `shared/schema/sceneSchema.{py,ts}` + `agent/events/vocabulary.py` |
| Frontend event dispatch | `frontend/hooks/useSceneActions.ts:routeSceneEvent` |
| Frontend chat + SSE parsing | `frontend/components/chat/SceneChat.tsx` |
| Inline control-panel rendering | `frontend/components/chat/ControlPanel.tsx` |
| Live scene + AnimationLoop owner | `frontend/components/scene/SceneCanvas.tsx` |
| Single-mutator boundary for THREE state | `frontend/components/scene/SceneController.ts` |
| Browser-side snapshot builder | `frontend/lib/sceneSetup.ts:buildSceneSnapshot` |
| EC2 lifecycle | `scripts/aws-ec2.sh` |
| Provisioning a fresh EC2 | `scripts/ec2-bootstrap.sh` |
| All v1 mocks tagged `MOCK` | `agent/store/scene_store.py` (zone map), `frontend/serialization/spatialSummary.ts` |

## v1 mocks still in place

- `ZONE_MAP` in `agent/store/scene_store.py` — hardcoded ground / lower
  / mid / upper y-ranges.
- `agent/store/scene_store.SceneStore.get_objects` — loops, doesn't
  batch.
- `agent/store/scene_store.SceneStore.get_objects_by_stage` — filters
  every object linearly, no index.
- `frontend/serialization/spatialSummary.ts:buildZoneMap` — same
  hardcoded zones.
- `frontend/lib/sceneSetup.ts:buildSceneSnapshot` — camera target is
  estimated from the camera's forward vector, not actually tracked
  (see "smaller fixes" in `docs/v2-backlog.md`).
- `objectIndex` is append-only — removed objects stay in the
  `fullIndex` forever. The Phase 5 hallucinated-uuid feedback masks
  this for now; tombstones in the v2 backlog.

## Hard rules (still in force)

From `.claude/CLAUDE.md`:

- **Never** call `scene.toJSON()` for agent context.
- **Never** create Three.js objects outside `ObjectFactory` /
  `LightFactory`.
- **Never** read `geometry.attributes` from the serializer.
- All factory-built objects tag `userData` with `label`, `geometryType`,
  `geometryArgs`, `stage`, `material`.
- v1 mocks tagged `// MOCK: replace in v2`.
- Tests RED-first.
- Commit format: `milestone(N): ...` for milestones, conventional
  commits (`feat:` / `fix:` / `chore:` / `docs:`) otherwise.
- Never `--no-verify`, `--amend` published commits, or destructive git
  ops without explicit user approval.

## Open backlog (next-up candidates)

See `docs/v2-backlog.md` for the full plan with effort estimates.

| Phase | Effort | Why pick this | Why skip |
|---|---|---|---|
| Phase 6 — per-object animation selection | ~3–4 hr | Demo polish; stems sway, fruit pulses, leaves drift instead of all-rotate | Bigger frontend Tickable work; no API cost change but real correctness risk |
| Phase 7 — live tool binding for Asset | ~4–5 hr | Closes the spatial-adjacency gap (anchors fix part of this; tools generalize) | Highest implementation risk in the backlog (multi-turn message shape) |
| Phase 8 — vision feedback loop | ~6–8 hr | Director sees what's actually rendered. Cheapest qualitative leap once anchors land | Headless WebGL screenshot from a hidden canvas is the load-bearing part; not much else |
| Smaller — precise camera target tracking | ~15 min | Snapshot fidelity — the orbit Tickable's center will be wrong otherwise | Only matters once user starts scripting non-trivial camera moves |
| Smaller — `objectIndex` tombstones | ~30 min | Removed-object uuids stop bloating Director context after many turns | No effect until the user runs 20+ prompt sequences |
| Smaller — custom camera positions | ~30 min | "show me from above" / "look from below" prompts | Director currently maps these to the closest of three presets, not always wrong |
| Smaller — undo/redo | ~2 hr | Each prompt is destructive today; would replay a previous snapshot | Real complexity is in the snapshot/replay loop and UI affordance |

## Suggested next moves (pick one)

1. **Phase 6**. Demo polish + would close out the "phases" naming
   continuity. The Tickable layer is well-isolated; risk is contained.
2. **A live verification pass with the user**. Three things shipped this
   session that haven't been hit by a real prompt: composition (flower /
   robot / tree), Phase 5 stops, control panels. One EC2 session would
   confirm all three.
3. **`objectIndex` tombstones**. ~30 min. Cleans up a hidden bloat
   problem before it becomes painful at higher prompt counts.

## Setup / run (for a fresh session or new machine)

```bash
# Clone + base setup
git clone https://github.com/eddie-nv/ag-webGL.git
cd ag-webGL
git clone https://github.com/affaan-m/everything-claude-code.git ~/everything-claude-code  # if .claude/ rules need refreshing

# Backend
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e ".[dev]"

# Frontend
cd frontend && npm install && cd ..

# Secrets
cp .env.example .env
$EDITOR .env  # paste ANTHROPIC_API_KEY

# Tests
.venv/bin/pytest -q                       # 103 pass
.venv/bin/pytest -m e2e                   # 3 pass against real LLM
cd frontend && npx tsc --noEmit && npm test  # 103 pass

# Run locally (heavy on a 8GB / 4-core machine -- prefer EC2 if
# possible, see scripts/aws-ec2.sh)
.venv/bin/uvicorn agent.main:app --reload --port 8000
cd frontend && npm run dev   # in another terminal
# Browser -> http://localhost:3000

# Run on EC2
./scripts/aws-ec2.sh launch    # creates instance + key + SG
./scripts/aws-ec2.sh ssh       # provision once via bootstrap script
./scripts/aws-ec2.sh tunnel    # forwards :3000 + :8000 from EC2 to local
./scripts/aws-ec2.sh stop      # stop instance (only EBS keeps billing)
```

## What to read first if you're picking this up cold

In order:

1. `README.md` — project overview, run instructions, hard rules.
2. `docs/agent-pipeline.md` — current 6-stage pipeline, narration
   shape, what each agent does. **Slightly outdated** — was written
   at M9 with 5 agents; Controls stage was added later. The 5-agent
   shape is described correctly, just add Controls at the end.
3. `docs/serialization-strategy.md` — why we don't use `scene.toJSON`,
   the hybrid payload contract.
4. `docs/event-vocabulary.md` — every event with example payloads.
   **Slightly outdated** — `scene:object_remove` and
   `scene:control_panel` were added after; treat the source of truth
   as `agent/events/vocabulary.py`.
5. `docs/v2-backlog.md` — what's next.
6. This file.

## Doc drift to clean up next session

- `docs/event-vocabulary.md` doesn't mention `scene:object_remove` or
  `scene:control_panel`.
- `docs/agent-pipeline.md` describes 5 agents; should describe 6 with
  Controls at the end + the per-item streaming behaviour from Phase 1.
- `README.md`'s "Project layout" section doesn't mention
  `agent/agents/controls.py`, `agent/agents/placement.py:Placer`,
  `frontend/components/chat/ControlPanel.tsx`,
  `frontend/lib/sceneSetup.ts:buildSceneSnapshot`.
- `PLAN.md` is the original M0–M9 plan. Phases 1–5 + composition +
  controls are after-the-fact -- their plan-equivalents live in
  individual commit messages. A "Phase Plan" doc consolidating these
  would be useful but isn't urgent.
