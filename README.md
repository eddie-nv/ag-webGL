# ag-webGL

Fullstack demo: Python (LangGraph) backend + TypeScript (Next.js) frontend.
Agent pipeline drives a Three.js scene via the AG-UI / CopilotKit event stream.

## Status

Bootstrapping. Build is staged across milestones — see `PLAN.md` for the full
roadmap. Each milestone ends with a commit of the form
`milestone(N): <description>`.

## Stack

- **Backend:** Python 3.11+, LangGraph, FastAPI, AG-UI protocol
- **Frontend:** Next.js (TypeScript), Three.js, CopilotKit, Vitest
- **Tests:** pytest (backend), vitest (frontend); 80%+ coverage target

## Hard rules

- Never call `scene.toJSON()` for agent context
- Every Three.js object must be created through `ObjectFactory`
- `ObjectFactory` must tag `userData` on every object it creates
- Mock is acceptable — every mock marked `// MOCK: replace in v2`
- Tests are written before implementation at every milestone

## Run (after Milestone 0)

```bash
# Backend
cd agent && pip install -e .
pytest
uvicorn main:app --reload

# Frontend
cd frontend && npm install
npm test
npm run dev
```
