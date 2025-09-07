# PM Team (Stub + Optional Autogen)

Dual-mode (local heuristic + real Autogen) multi-agent example for project management workflows. Provides:

- Deterministic lightweight Python-only agents (no API calls) for fast local iteration.
- Optional real `autogen` LLM-powered agents (enable with `--autogen`).
- Orchestrated sprint planning, release coordination, and stakeholder communication.
- Event bus, audit logging (JSONL), metrics accumulation, risk scoring, multi-blocker mitigation.
- Graceful fallback when no `OPENAI_API_KEY` is present.

## Agents

| Agent                    | Responsibilities                                                                              | Key Outputs                            |
| ------------------------ | --------------------------------------------------------------------------------------------- | -------------------------------------- |
| Sprint Planner           | Breaks initiative into tasks, assigns story points, risk levels, adds mitigation for blockers | Task list, risk scores, aggregate risk |
| Release Coordinator      | Proposes release window, milestone, rollback stub, release notes selection                    | Release summary JSON                   |
| Stakeholder Communicator | Translates plan/release into concise business update                                          | Stakeholder summary (plain text)       |

### Execution Flow

1. User supplies initiative + optional one or more `--blocker` flags.
2. Planner creates baseline sprint plan (tasks include `risk_score`).
3. Each blocker spawns a mitigation task; aggregate risk recomputed.
4. Release Coordinator drafts release window, milestone, notes.
5. Stakeholder Communicator produces business-facing summary.
6. Event bus fires events (`PLAN_CREATED`, `BLOCKER_ADDED`, `RELEASE_DRAFTED`, `STAKEHOLDER_SUMMARY`, `RUN_COMPLETED`).
7. Audit logger appends JSONL entries; metrics updated (plans_created, blockers_recorded, last_points).
8. (Optional) Real Autogen agents mirror the same flow; raw LLM outputs are shown.

## Project Structure (src layout)

```
.
  README.md
  pyproject.toml
  LICENSE
  src/
    pm_team/
      __init__.py
      base.py
      config.py
      sprint_planner.py
      release_coordinator.py
      stakeholder_communicator.py
      orchestration.py
      output_writer.py
      autogen_integration.py   # Only used when --autogen and Autogen installed
      cli.py                   # Entry point (console script: pm-team)
  examples/
    run_demo.py                # Thin wrapper to CLI
  tests/
    test_orchestration.py
  outputs/                     # Generated artifacts (gitignored)
  <project_slug>/            # Per-project directory (audit_log.jsonl, project.json, run folders)
```

Legacy directory `autogen_pm_team/` has been deprecated (left temporarily for migration reference). Source now lives under `src/pm_team`.

## Quick Start (Stub Mode)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pm-team "Build an AI-powered analytics dashboard"
```

## Real Autogen Integration

```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL_NAME="gpt-4o-mini"   # optional
pm-team "New initiative" --autogen
```

If no key is set, run proceeds in stub mode with a warning.

## Feature Highlights

- Multi-blocker support (`--blocker` repeatable)
- Aggregate risk scoring
- JSONL audit log (`audit_log.jsonl`)
- Event bus + metrics
- Timezone-aware timestamps
- Real Autogen fallback detection
- Raw LLM output capture
- Structured artifact persistence into `outputs/` (plan, release, metrics, stakeholder summary, autogen raw)
- Multi-project support (separate audit + runs under `outputs/<project>/`)

## Configuration

Edit `src/pm_team/config.py` or set env vars:

- `OPENAI_API_KEY`
- `OPENAI_MODEL_NAME`
- `PM_TEAM_OUTPUT_ROOT` (optional custom output directory)
- `PM_TEAM_NONINTERACTIVE=1` (skip interactive project prompt; uses `default`)

## Multi-Project Usage

Create a named project (auto-creates directory & metadata):

```bash
pm-team --create-project FinanceRevamp "Initial architecture baseline"
```

Run another initiative in the same project:

```bash
pm-team --project FinanceRevamp "Add billing integration" --blocker compliance --blocker networking
```

List projects (simple file system inspection):

```bash
pm-team placeholder --list-projects
ls outputs
cat outputs/finance_revamp/project.json

# Prune old runs keeping last 5 only (per project) and emit JSON
pm-team --project FinanceRevamp "Refactor payment gateway" --max-runs 5 --json > latest.json
```

Non-interactive default project (CI / scripts):

```bash
PM_TEAM_NONINTERACTIVE=1 pm-team "Nightly regression hardening"
```

## CLI Flags

| Flag                    | Purpose                                           |
| ----------------------- | ------------------------------------------------- |
| `initiative`            | Positional description of the work initiative     |
| `--blocker X`           | Add one or more blockers (repeat flag)            |
| `--autogen`             | Enable real Autogen agents (needs OPENAI_API_KEY) |
| `--project NAME`        | Use (or auto-create) existing project             |
| `--create-project NAME` | Force creation of a new project with NAME         |
| `--list-projects`       | List existing projects and exit                   |
| `--json`                | Emit machine-readable JSON instead of text UI     |
| `--max-runs N`          | After writing artifacts prune to last N runs      |

## Environment Variables

| Variable                 | Effect                                                    |
| ------------------------ | --------------------------------------------------------- |
| `OPENAI_API_KEY`         | Enables real Autogen LLM mode                             |
| `OPENAI_MODEL_NAME`      | Override default model (gpt-4o-mini)                      |
| `PM_TEAM_OUTPUT_ROOT`    | Change base outputs directory                             |
| `PM_TEAM_NONINTERACTIVE` | If `1`, skip interactive project selection; use `default` |

## Roadmap

1. Parse & merge Autogen JSON into internal model.
2. Add retrieval augmentation.
3. Implement probabilistic risk delay estimator.
4. Concurrency safety (file locking) for parallel runs.
5. Web dashboard for live visualization.
6. Optional Autogen streaming + JSON schema validation.

## Outputs

Each run creates a timestamped folder under `outputs/<project_slug>/` containing:

- `plan.json`
- `release.json`
- `metrics.json`
- `aggregate_risk.txt`
- `blockers.txt` (if any)
- `stakeholder_summary.txt`
- `manifest.json`
- `autogen/` raw LLM responses when `--autogen`
  Per project: `project.json` (metadata, run counter) and `audit_log.jsonl` (audit events).

## Testing

## Web UI (Angular + FastAPI)

Directory `frontend/pm-team-ui` contains an Angular 20 scaffold (standalone components). A lightweight FastAPI backend (`pm_team.api`) exposes project and run artifacts:

Endpoints:

- `GET /projects`
- `GET /projects/{slug}/runs`
- `GET /projects/{slug}/runs/{run_id}`
- `GET /projects/{slug}/runs/{run_id}/artifact/{name}`

Run backend (development):

```bash
uvicorn pm_team.api:app --reload
```

Then adapt Angular app to call these endpoints (add service under `frontend/pm-team-ui/src/app`).

```bash
pytest -q
```

Add `-k project` to run only project-related tests once added.

## Retention & Cleanup

- `--max-runs N` prunes oldest run folders (implemented).
- Set `PM_TEAM_AUDIT_MAX_BYTES` to rotate `audit_log.jsonl` once it exceeds the byte threshold (creates timestamped rollover files).
- Future: `pm-team --prune` command for explicit retention enforcement.

## License

MIT (see `LICENSE`).

---

Migration Note: If you previously imported modules via `autogen_pm_team.pm_team.*`, update imports to `pm_team.*` after installing editable with `pip install -e .`.
