# Autogen Project Management Agent Team

(README moved from `autogen_pm_team/README.md` — this is now the root project overview.)

A dual-mode (stub + real Autogen) multi-agent example for project management workflows. It provides:

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

## Project Structure

```
.
  README.md
  pyproject.toml
  autogen_pm_team/
    requirements.txt
    pm_team/
      base.py
      config.py
      autogen_integration.py
      sprint_planner.py
      release_coordinator.py
      stakeholder_communicator.py
      orchestration.py
      output_writer.py
    examples/
      run_demo.py
    tests/
      test_orchestration.py
    outputs/               # Generated artifacts (can be gitignored later)
```

## Quick Start (Stub Mode)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r autogen_pm_team/requirements.txt
python autogen_pm_team/examples/run_demo.py "Build an AI-powered analytics dashboard"
```

## Real Autogen Integration

```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL_NAME="gpt-4o-mini"   # optional
python autogen_pm_team/examples/run_demo.py "New initiative" --autogen
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

## Configuration

Edit `autogen_pm_team/pm_team/config.py` or set env vars:
- `OPENAI_API_KEY`
- `OPENAI_MODEL_NAME`
- `PM_TEAM_OUTPUT_ROOT` (optional custom output directory)

## Roadmap

1. Parse & merge Autogen JSON into internal model.
2. Add retrieval augmentation.
3. Implement probabilistic risk delay estimator.
4. Add CLI subcommands and JSON output flag.
5. Add retention policy for `outputs/` directory.
6. Web dashboard for live visualization.

## Outputs

Each run creates a timestamped folder under `autogen_pm_team/outputs/` containing:
- `plan.json`
- `release.json`
- `metrics.json`
- `aggregate_risk.txt`
- `blockers.txt` (if any)
- `stakeholder_summary.txt`
- `manifest.json`
- `autogen/` raw LLM responses when `--autogen`

## License

MIT (add a LICENSE file if distributing externally).
