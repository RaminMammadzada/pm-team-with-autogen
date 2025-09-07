# GitHub Instructions & Engineering Guide

> Project: pm-team-with-autogen  
> Stage: Early iterative build – core planning artifacts, conversational assistant, mutation modes, diffing.

This guide explains how we build, reason about, and extend this repository. It captures the engineering practices already applied plus the conceptual model driving future work.

---

## 1. Vision Snapshot

An agent‑augmented planning workspace combining:

- Structured planning artifacts (plan / release / metrics / stakeholder) per "run" (initiative execution snapshot).
- Conversational control surface (chat) that can _query_ status & risk and _mutate_ the plan (add blocker, reprioritize, update status) safely.
- Multi‑tier intelligence: heuristic summarizer → OpenAI LLM → optional Autogen agent (environment‑flagged) with graceful fallback chain.
- Analytical capability: diff any two plan versions (runs) to expose added / removed / modified tasks and aggregate risk delta.

Roadmap (high‑level): streaming responses, multi‑turn refinement loop (planner/critic), plan version lineage persistence, richer analytics (burndown, velocity validation), retrieval augmentation, agent actions / tool execution.

---

## 2. Architecture Overview

Backend (Python / FastAPI):

- Endpoints: project & run creation, artifact retrieval, chat (`/chat`), plan diff (`/plan-diff`).
- Artifact persistence: JSON files under per-run directory: `plan.json`, `release.json`, `metrics.json`, `stakeholder.json`, plus `conversation.json`.
- Orchestration layer generates initial artifacts (planning, release, metrics, stakeholder perspectives).
- Chat pipeline: request → optional plan mutation (based on mode) → agent reply (heuristic/LLM/autogen) → conversation persisted.

Frontend (Angular 20, standalone components & signals):

- Service wraps API calls (projects, runs, plan, chat, diff).
- UI panels: initiatives list, plan table, chat, diff comparator.
- Chat modes toolbar (query vs mutation modes) + contextual inputs.
- Auto-scroll effect for conversation continuity.

### Technology Stack (Current & Planned)

**Backend**

- Language: Python 3.11+
- Framework: FastAPI (async, typed request models)
- Server: Uvicorn (dev reload)
- Persistence: JSON artifact files (plan / release / metrics / stakeholder / conversation)
- AI Layers: OpenAI Chat Completions, optional Autogen (single-turn), heuristic fallback (`ConversableAgentBase`)
- Config: Environment variables (no hardcoded secrets)
- Packaging: `pyproject.toml` + `requirements.txt` (migration path to fully pinned lock)

**Frontend**

- Framework: Angular 20 (standalone APIs, no NgModules)
- Language: TypeScript (strict)
- State: Angular Signals (lightweight reactive store)
- Styling: SCSS
- Networking: Angular `fetch`/`HttpClient` (service abstraction)
- UI Patterns: Optimistic updates, scroll anchoring, mode‑driven inputs

**Tooling & Quality**

- Git + Conventional commit prefixes
- Planned tests: `pytest` (unit for pure functions, integration for chat/mutations)
- Lint / Type Safety: Python type hints (future mypy), TS strict compiler
- Observability (future): structured log lines, mutation audit ledger

**Planned Enhancements**

- Streaming (SSE or chunked HTTP)
- Embedding / retrieval augmentation layer
- Multi-turn planner/critic agents
- Snapshot version history (immutable plan lineage)
- Analytics: burndown simulation, velocity accuracy metrics, risk trend charts
- Security: secret scanning pre-commit, role-based view constraints

**Design Principles Recap**

- Graceful degradation across intelligence layers
- Pure functions for domain mutations; side-effects isolated to API boundary
- Minimal surface first; additive evolution (avoid breaking schemas)
- Human-inspectable artifacts to accelerate iteration

---

## 3. Key Domain Concepts

| Concept          | Description                                                                                                           |
| ---------------- | --------------------------------------------------------------------------------------------------------------------- |
| Project          | Top-level container grouping multiple planning "runs" (initiatives executed or re-generated).                         |
| Run / Initiative | A single generated planning snapshot. Immutable after creation except for in-place task mutations (current approach). |
| Plan             | Core artifact containing initiative metadata, tasks array, risk data, blockers, velocity assumptions.                 |
| Release          | Release notes / candidate deliverables artifact.                                                                      |
| Metrics          | Estimation, velocity assumptions, derived sprint counts.                                                              |
| Stakeholder      | Communication-oriented narrative (future: role-personalized).                                                         |
| Conversation     | Chronological message list (user + agent).                                                                            |
| Chat Modes       | Operation modes: informational (status, risk) or mutating (add_blocker, reprioritize, update_status).                 |
| Diff             | Structural comparison between two runs' `plan.json` artifacts.                                                        |

---

## 4. Intelligence & Fallback Chain

1. Autogen (if `USE_AUTOGEN=1` and `OPENAI_API_KEY` present) – single-turn assistant wrapper.
2. Direct OpenAI Chat Completion (model resolved via `PM_TEAM_LLM_MODEL` → `OPENAI_MODEL_NAME` → default).
3. Heuristic agent (`ConversableAgentBase`) – deterministic summary & intent mapping, domain-aware.

All fallbacks degrade _gracefully_: no crashes leak to client; heuristic append includes provenance note when used due to failure.

---

## 5. Implemented Chat Modes

| Mode             | Input(s)                                 | Effect                                                 |
| ---------------- | ---------------------------------------- | ------------------------------------------------------ |
| (default / null) | message text                             | Pure query (status, risk, tasks, general).             |
| add_blocker      | blocker (string)                         | Appends blocker to plan blockers list.                 |
| reprioritize     | order (space or comma list of task IDs)  | Reorders tasks by explicit sequence (others appended). |
| update_status    | statuses mapping (e.g. `T1=done T2=wip`) | Updates `status` field of matching tasks.              |

System updates for each mutation are pushed into conversation for transparency.

---

## 6. Plan Mutation Principles

- Pure functional helpers in `plan_ops.py` (deterministic, no side effects beyond returned modified object).
- API layer: load plan → apply mutation → persist updated plan → append system update message.
- Validation (current): minimal; assumes IDs exist. Future: strict validation + rollback log.

---

## 7. Diff Mechanism

`diff_plans(old_plan, new_plan)` returns:

- added_tasks, removed_tasks, modified_tasks (changed any of title / estimate / risk / status / priority / description).
- aggregate risk delta summary.
  Frontend displays categorized lists and risk delta.

---

## 8. Engineering Practices Applied

- Iterative vertical slices (each enhancement spans backend + frontend + persistence).
- Fallback-first resilience (LLM unavailable ≠ degraded UX).
- Environment-variable driven configuration to avoid hardcoding secrets / models.
- Small, composable mutation functions instead of embedding logic in endpoint routes.
- Deterministic heuristics for baseline functionality enabling offline / keyless operation.
- JSON artifact storage for inspectability and easy diffing without DB overhead (early phase optimization of iteration speed).
- Explicit mode signaling in chat payload to separate _intent parsing_ concerns from _action execution_.
- UI optimism: immediate scroll + rendering; agent response appended when ready (future: streaming for latency masking).
- Strict separation of domain summarization vs generation (summary fed as context string to models / heuristics).
- Minimal coupling: heuristics ingest only textual summary, making replacement with embedding/RAG trivial later.
- Principled naming (`plan_ops`, `plan_diff`, `conversation`) for discovery.
- Commit messages: pragmatic conventional style `feat(scope): description` / `fix:` / `chore:` etc.

---

## 9. Environment Variables

| Variable            | Purpose                                      | Notes                               |
| ------------------- | -------------------------------------------- | ----------------------------------- |
| OPENAI_API_KEY      | Enables OpenAI-based LLM tier.               | Required for Autogen too.           |
| PM_TEAM_LLM_MODEL   | Primary model override (e.g. `gpt-4o-mini`). | Highest precedence.                 |
| OPENAI_MODEL_NAME   | Secondary model fallback variable.           | Optional.                           |
| USE_AUTOGEN         | `1` / `true` to activate Autogen wrapper.    | Requires OPENAI_API_KEY.            |
| PM_TEAM_OUTPUT_ROOT | Root directory for persisted projects/runs.  | Defaults to internal path if unset. |

---

## 10. Local Development

(Assumes Python 3.11+ and Node 18+.)

Backend (FastAPI):

1. Create venv & install deps (see `requirements.txt` if present; otherwise add dependencies: `fastapi`, `uvicorn`, `openai`).
2. Run server: `uvicorn src.pm_team.api:app --reload`.
3. Set env vars before launching if using LLM features.

Frontend (Angular):

1. Install dependencies: `npm install` inside `frontend/pm-team-ui`.
2. Run dev server: `npm start` or `ng serve` (depending on configured scripts).
3. App communicates with backend (configure API base URL in the service if necessary).

### Background Run Helper
Backend (background):
```
nohup uvicorn src.pm_team.api:app --host 0.0.0.0 --port 8000 --reload > backend.log 2>&1 & echo $! > backend.pid
```
Stop backend:
```
kill $(cat backend.pid) && rm backend.pid
```
Frontend (background):
```
cd frontend/pm-team-ui && nohup ng serve --port 4200 --host 0.0.0.0 > ../../frontend.log 2>&1 & echo $! > ../../frontend.pid
```
Stop frontend:
```
kill $(cat frontend.pid) && rm frontend.pid
```
Health check (quick grep):
```
grep -i 'Uvicorn running' backend.log && grep -i 'Application bundle generation complete' frontend.log
```
Force free ports:
```
lsof -ti:8000 -ti:4200 | xargs kill
```

---

## 11. Directory Layout (Key Parts)

```
src/pm_team/
  api.py                # FastAPI endpoints
  conversation.py       # Conversation persistence + agent reply orchestration
  base.py               # Heuristic agent stub
  autogen_agent.py      # Optional Autogen wrapper
  plan_ops.py           # Mutation helpers
  plan_diff.py          # Diff computation
frontend/pm-team-ui/
  src/app/              # Angular root app, signals, components
```

Generated data stored under an output root (project → run → artifacts + `conversation.json`).

---

## 12. Adding a New Chat Mode (Pattern)

1. Define mutation helper (pure) in `plan_ops.py` (e.g., `def escalate_risk(plan, task_ids): ...`).
2. Extend backend request model (`ChatPost`) with needed field(s).
3. Update `/chat` route: detect `mode == "escalate_risk"`, apply helper pre‑agent.
4. Append a system update message summarizing change.
5. Update frontend `data.service.ts` to pass new mode + inputs.
6. Add UI control / input field in `app.html` and logic in `app.ts`.
7. (Optional) Extend heuristic agent to recognize related queries.

---

## 13. Extensibility Roadmap

| Area                 | Planned Direction                                                                        |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Streaming            | Server‑Sent Events / chunked responses from OpenAI & heuristic for real-time UI updates. |
| Multi-Turn Reasoning | Planner / Critic loop (bounded turns, token guardrails).                                 |
| Retrieval            | Embedding index of prior runs / tasks for contextual enrichment.                         |
| Version History      | Persist snapshots on every mutation instead of in-place edit for true lineage.           |
| Analytics            | Burndown simulation, velocity accuracy scoring, risk trend charts.                       |
| Auditability         | Append mutation ledger separate from conversation for compliance trace.                  |
| Role Views           | Tailored stakeholder artifact slices (engineering, product, leadership).                 |
| Tool Actions         | Limited command/action execution (e.g., create ticket) with approval gating.             |

---

## 14. Quality & Testing Approach (Current & Future)

Current: manual exploratory testing per vertical slice; deterministic heuristics facilitate reproducibility.
Planned:

- Unit tests for `plan_ops` (pure functions) & `plan_diff` to lock correctness.
- Lightweight integration test spinning up FastAPI test client for chat mutation flows.
- Snapshot tests for heuristic status response.

---

## 15. Security & Secrets

- No secrets committed; rely on environment variables.
- Rejects: storing API keys in artifacts or conversation history.
- Future: secret scanning pre-commit hook.

---

## 16. Contribution Workflow

1. Create issue (feature / enhancement / refactor / defect) with concise acceptance criteria.
2. (Optional) Design note if change affects artifacts or chat contract.
3. Branch naming: `feat/<short>` or `fix/<short>` etc.
4. Keep PRs small (single vertical slice).
5. Include reasoning in description if modifying heuristics / fallback chain.
6. After merge, verify run generation + chat regression manually.

---

## 17. Coding Style Highlights

Python:

- Prefer small pure functions; side effects only in API layer.
- Keep artifact schema stable; extend with additive fields (avoid breaking old runs).
- Graceful exception handling – fallback rather than crash.

Angular:

- Signals for reactive state (no heavy global store yet).
- Standalone components / lean templates; keep service as single API facade.
- Optimistic UI interactions; status updates surfaced via system messages.

Commit Style Examples:

- `feat(chat): introduce update_status mode`
- `fix(plan): correct priority ordering comparator`
- `chore(ui): adjust spacing in plan table`

---

## 18. Heuristic Agent Philosophy

Goal: Provide baseline utility _offline_ and enrich model context succinctly. The heuristic extracts structured lines (e.g., INITIATIVE, RISK) → transforms into concise natural language for status queries. This ensures continuity when LLM unavailable and reduces token usage when it is.

---

## 19. Troubleshooting

| Symptom                                         | Cause               | Resolution                                      |
| ----------------------------------------------- | ------------------- | ----------------------------------------------- |
| Chat replies end with `(Set OPENAI_API_KEY...)` | Missing key         | Export `OPENAI_API_KEY`.                        |
| Autogen not used                                | `USE_AUTOGEN` unset | Set `USE_AUTOGEN=1`.                            |
| Plan diff empty though tasks changed            | Same run compared   | Select two distinct runs.                       |
| Reprioritize failed silently                    | Task IDs mismatch   | Confirm IDs exist; future validation will warn. |

---

## 20. Open Questions (Deliberately Deferred)

- Snapshot granularity vs. mutation in-place tradeoff.
- Cost model for multi-turn reasoning (token budgets, interrupts).
- Unified schema validation layer (Pydantic models for artifacts?).
- Access control / multi-user tenancy.

---

## 21. Quick Start Checklist

- [ ] Clone repo & install backend + frontend deps
- [ ] Set `OPENAI_API_KEY` (optional for advanced intelligence)
- [ ] (Optional) Set `USE_AUTOGEN=1`
- [ ] Start backend & frontend dev servers
- [ ] Create a project and first run
- [ ] Ask: "what is happening in the project?" → receive clean status summary
- [ ] Try mutation modes: add blocker, reprioritize, update task statuses
- [ ] Compare two runs via diff panel

---

## 22. License / Compliance

(Insert license guidance here if/when selected.)

---

## 23. Maintaining This Document

Update this file whenever you:

- Introduce a new chat mode
- Add artifact fields impacting summaries
- Change fallback hierarchy
- Implement major roadmap item

---

_End of GitHub Instructions Guide_  
This living document should evolve with the system – keep it tight, actionable, and architecture‑reflective.
