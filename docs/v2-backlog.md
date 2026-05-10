# v2 Backlog — Phased Plan

This file picks up where Phase 4 left off. Each phase is independently
shippable and ordered roughly by `effort × clarity`. Phases 5 and 6 are
straightforward; Phases 7 and 8 are real architectural bumps.

Estimated efforts assume a single focused session at this codebase's
current pace. Costs are sonnet-4.6 prices on the Anthropic API.

---

## Phase 5 — Stop camera spin (and any animation by name)

**Problem.** Once a camera spin starts, the only way to stop it is a page
reload. Same for object animations once Phase 6 lands. The vocabulary
already has `scene:animation_stop`, but no agent emits it.

**Effort:** ~30 min. Smallest leverage win.

**Changes:**

- `agent/agents/types.py` — add `CameraAction.stopSpin: bool = False`.
- `agent/agents/animation.py` — when `cameraAction.stopSpin`, emit
  `scene:animation_stop` with `uuid="camera"`.
- `agent/prompts/director.md` — few-shot example for "stop the camera",
  "freeze the view", "halt the rotation".
- For object animations: extend `BriefUpdate` with optional
  `stopAnimation: bool`; Asset emits `scene:animation_stop` with the
  matching `uuid`.

**Verification:** prompt sequence "spin the camera" → "stop the camera"
should orbit then halt. `[scene] event in: scene:animation_stop` line in
DevTools.

**Risk:** none -- the wire types and SceneController paths already exist.

---

## Phase 6 — Per-object animation selection

**Problem.** Animation today is rotate-y on every object when
`brief.animate=true` and multi-stage. A growing tomato plant looks identical
to a spinning dreidel. Worse, things that should be static (the soil
mound, the camera target) rotate too.

**Effort:** ~3–4 hr.

**New Tickable factories** in `frontend/components/scene/SceneController.ts`:

| `animationType` | behavior                                          | params used                |
|-----------------|---------------------------------------------------|----------------------------|
| `rotate`        | spin on `axis`                                    | `axis`, `duration`         |
| `sway`          | gentle ±30° y-rotation, sine-wave, period=duration | `axis`, `duration`         |
| `drift`         | translate from→to and back, looped                | `from`, `to`, `duration`   |
| `scale`         | scale 0→1 over duration (one-shot, no loop)       | `duration`, `loop=false`   |
| `pulse`         | scale oscillates 0.95↔1.05                        | `duration`                 |
| `fade-in`       | opacity 0→1                                       | `duration`, `loop=false`   |

The schema (`AnimationStartPayload.animationType: str`) is already
free-form; adding new types is purely a SceneController + factory change.

**Pipeline changes:**
- New agent `agent/agents/animator.py`: per object in the manifest, picks
  one of the animation types. Either via a small per-object LLM call or
  via a deterministic rule (e.g. label contains "stem"/"trunk" → sway,
  label contains "leaf"/"flower" → pulse, label contains "fruit" → scale,
  default → static i.e. no event).
- The current `agent/agents/animation.py` becomes the deterministic
  fallback; the LLM-driven version sits in front when `brief.animate=true`.

**Tests:**
- Unit test per Tickable factory (call tick(delta) repeatedly, assert
  expected transform after N seconds).
- Animator agent test with stub LLM returning various types.

**Risk:** medium. Tickable correctness is finicky -- a sway that
accumulates `delta * speed` without bounds will drift; oscillations need
to be `Math.sin(t)`, not integrated. Tests catch this.

**Cost increase:** if LLM-driven, +1 call per object during Animation
stage. Tomato (5 objects) goes from 0 to 5 extra calls/run ≈ +$0.01.

---

## Phase 7 — Live tool binding for the Asset agent

**Problem.** `agent/prompts/asset.md` lists `get_manifest`, `get_object`,
`get_zone_map` as "tools available", but they're documentation only. The
Asset agent picks geometry/material for each item with **no awareness of
adjacent objects**. So a "leaf" placed next to a "stem" doesn't know
where the stem actually is; it just lands at zone-midpoint with x/z
offset by index.

The store_tools wrappers from M2 (`agent/store/store_tools.py`) already
exist. Phase 7 connects them to the model.

**Effort:** ~4–5 hr.

**Approach.** langchain-anthropic supports tool calling via
`ChatAnthropic.bind_tools(...)`. Inside `agent/agents/asset.py`:

```python
def run_asset_item(store, model, item, zone_map):
    bound = model._model.bind_tools(create_store_tools(store))
    messages = [HumanMessage(content=_build_prompt(item.label, item.zone, item.stage))]
    while True:
        response = bound.invoke(messages)
        messages.append(response)
        if not response.tool_calls:
            break
        for call in response.tool_calls:
            result = ...  # dispatch to store_tools by name
            messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
    # Final response: AssetDetails JSON
    return AssetDetails.model_validate_json(_extract_json(response.content))
```

**Pipeline changes:**
- `agent/llm.py`: expose the underlying ChatAnthropic so Asset can
  `bind_tools` on it. (Currently encapsulated.)
- `agent/agents/asset.py`: tool-loop variant of `iter_asset_items`.
- `agent/prompts/asset.md`: rewrite tool docs from "for v2 binding" to
  "you may call these before responding"; add few-shot example of a
  multi-turn tool-using exchange.

**Tests:**
- Stub model that returns scripted tool_calls then a final response.
- Verify that the right store methods are called and results are fed back.
- E2e: ask agent to "place a leaf next to the stem" and verify position
  proximity (using place_in_zone-derived coords, not LLM-chosen, so this
  may require relaxing place_in_zone's deterministic spread).

**Risk:** high. Tool-calling changes the message shape (assistant turns
contain `content_blocks` with tool_use entries; ToolResult blocks in
user turns). The `_extract_json` helper needs to handle the new shape.
Token cost grows because each tool round-trip re-sends the full message
history.

**Cost increase:** Asset call goes from ~3-4k tokens to ~6-10k per item
depending on tool depth. For a 5-object scene: roughly +$0.05–0.10 per
run. Real but acceptable.

**Why this is the highest-leverage phase.** Closes the biggest correctness
gap: agent reasoning about spatial adjacency. Once Asset can ask
"where's the stem?" before placing the leaf, the demo stops looking
randomly composed.

---

## Phase 8 — Vision feedback loop

**Problem.** The agents have no idea what the rendered scene actually
looks like. They reason from labels and the manifest, not from pixels.
For complex scenes ("show how a volcano erupts") this means choices
that *plan* well but *render* poorly: occluded objects, weird
intersections, washed-out colors, scale mismatches between adjacent
objects. The Director cannot recover unless the user catches and
re-prompts.

**Effort:** ~6–8 hr. Largest qualitative leap, largest infra change.

**Architecture.**

```
prompt N+1
   │
   ▼
frontend POST /agui  ───► includes:  prompt
                                     sceneSnapshot   (state)
                                     sceneScreenshot (PNG, base64)
                                     │
                          ▼
              backend pipeline
                     │
                     ▼
              Director sees:
              - text prompt
              - scene_state (already added in Phase 2)
              - rendered image  <-- new
              and can plan with visual context
```

**Frontend** (`frontend/lib/sceneSetup.ts` or new helper):

```ts
export function captureSnapshotImage(setup: SceneSetup): string {
  // Render once into an offscreen canvas, return base64 PNG.
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true })
  renderer.setSize(512, 384)
  renderer.render(setup.scene, setup.camera)
  const dataUrl = renderer.domElement.toDataURL('image/png')
  renderer.dispose()
  return dataUrl.split(',')[1] // strip "data:image/png;base64,"
}
```

`SceneChat.send()` would attach this to the POST body. 512×384 keeps
vision tokens around 800–1200 per call.

**Backend** (`agent/main.py` + `agent/agents/director.py`):

```python
# main.py: pluck the screenshot
screenshot_b64 = payload.get("sceneScreenshot")

# director.py: pass it through
def run_director(prompt, store, model, screenshot=None):
    parts = [{"type": "text", "text": _build_prompt(prompt, store.get_manifest())}]
    if screenshot:
        parts.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": screenshot}
        })
    raw = model.invoke_multimodal(parts)
    ...
```

`agent/llm.py` needs an `invoke_multimodal(parts)` method that builds the
right Anthropic message shape (langchain-anthropic supports image content
blocks via `HumanMessage(content=[...])`).

**Director prompt update:**
- New section: "If a current scene image is attached, **use it**. Look
  at scale mismatches, occlusion, color clashes. Plan changes
  proportional to what you see, not just what was added."

**Tests:**
- Unit test for captureSnapshotImage: mock WebGLRenderer, assert
  base64 string returned.
- Director test with stub LLM that ignores the image (just confirms
  the multimodal path doesn't break).
- Manual e2e: send a deliberately broken scene state (huge tomato,
  tiny stem) and prompt "fix the proportions". Without vision, Director
  can't tell anything is wrong. With vision, it should emit updates
  reducing the tomato scale.

**Risk:** medium. WebGL screenshot in jsdom for unit tests is awkward
(WebGLRenderer is mocked). The SSR rebuild needs `preserveDrawingBuffer`
on the **main** renderer too if we want to capture during rendering
(otherwise the framebuffer is cleared each frame). Currently we don't,
so the capture creates a throwaway renderer just for the screenshot --
~50ms each.

**Cost increase:** 1 image per Director call ≈ 1000 vision tokens at
sonnet-4.6 vision pricing (~$3/MTok input). +$0.003 per prompt. Trivial.

**Why this is the right closer.** Phase 7 makes the agents reason
better; Phase 8 makes them see what they're producing. Together they
cover the two reasons today's scenes look "off" -- bad spatial sense
and no visual feedback.

---

## Smaller fixes (any time, no strict order)

These don't need a full phase. Each is a focused commit.

### Track the camera lookAt target precisely

`SceneController.cameraTarget` is currently set on every `moveCamera`
call but defaulted to `(0, 0.8, 0)` initially. The frontend snapshot
estimates target from the camera's forward vector. Better: have
`SceneCanvas` initialize `controller.cameraTarget` from the same value
the Layout preset uses, and serialize it explicitly into the snapshot.
~15 min.

### objectIndex tombstones

`objectIndex` is append-only by plan. Removed objects stay in
`fullIndex` forever. After 50 turns the manifest has lots of dead
uuids and the Director's prompt context grows. Add a `tombstones`
set so `getAll()` excludes them. Director prompt sees only live
objects. ~30 min.

### Hallucinated-uuid feedback

If the Director outputs a `removals[]` or `updates[]` uuid that doesn't
exist in the snapshot, `SceneController.removeObject(ghost)` /
`.updateObject(ghost, ...)` silently no-op. Add a `console.warn` in
the router (or backend log line) so the failure is visible during
debugging. ~10 min.

### Stop spinning a specific object

Phase 5 covered camera + bulk stop, but "stop spinning the cube" needs
the Director to identify the right uuid. Add few-shot example showing
`updates: [{uuid: ..., stopAnimation: true}]` and an extension to
BriefUpdate. ~30 min if Phase 5 lands first.

### Custom camera positions

`brief.cameraStyle` is restricted to `wide / closeup / orbit`. Add
`brief.cameraAction.moveTo: Vec3` and `cameraAction.lookAt: Vec3` for
"show me from above" / "look at it from below" prompts. Layout prefers
explicit moveTo over the preset. ~30 min.

### Undo / redo via snapshot history

Each turn already captures a snapshot. Buffer the last N (say 20) on
the frontend, and add `↶ undo` / `↷ redo` buttons in `SceneChat`. On
undo, replay the previous snapshot's events (full rebuild) without
hitting the LLM. ~2 hr.

---

## Recommended order (if executing top-down)

1. **Phase 5** + **stop spinning a specific object** + **hallucinated-uuid
   feedback** -- one ~1 hr commit, finishes the "command vocabulary".
2. **Phase 6** -- adds visual variety. Demo starts to feel less artificial.
3. **Phase 8** before **Phase 7**. Counterintuitive -- but vision is
   cheap to add and pays for itself by making prompt iteration faster.
   Phase 7 is heavier and benefits from already having visual feedback
   when validating tool-driven placements.

If you want one phase that gives the biggest single-shot improvement,
it's Phase 7 (live tool binding). If you want the lowest-risk shipped
demo, do Phases 5 → 6 → 8 and skip 7 for v3.
