# Autogen Project Management Agent Team

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
autogen_pm_team/
   README.md
   requirements.txt
   pyproject.toml
   pm_team/
      __init__.py
      base.py                 # Lightweight local agent base
      config.py               # LLM / API key config
      autogen_integration.py  # Real Autogen wiring
      sprint_planner.py
      release_coordinator.py
      stakeholder_communicator.py
      orchestration.py        # Event bus, audit, metrics, orchestration
   examples/
      run_demo.py             # CLI demo (--blocker, --autogen)
   tests/
      test_orchestration.py   # Basic unit test
```

## Quick Start (Stub Mode)

Create virtual environment & install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python autogen_pm_team/examples/run_demo.py "Build an AI-powered analytics dashboard for customer churn insights"
```

## Real Autogen Integration

Already included. To enable LLM-backed agents:

```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL_NAME="gpt-4o-mini"   # optional
python autogen_pm_team/examples/run_demo.py "New initiative" --autogen
```

If `OPENAI_API_KEY` is absent, the run still completes using stub logic; a warning is shown.

## Feature Highlights

- Multi-blocker support (`--blocker` can repeat)
- Aggregate risk scoring (sum of task risk_score)
- JSONL audit log (`audit_log.jsonl`)
- Event bus for extensibility
- Metrics snapshot appended to run result
- Timezone-aware timestamps (UTC ISO8601)
- Real Autogen fallback detection
- Raw LLM output capture (planner/release/stakeholder)

## Configuration

`pm_team/config.py` controls:

- Model name (`OPENAI_MODEL_NAME` env var)
- API key detection (`OPENAI_API_KEY` env var)
- Fallback behavior (returns `False` to disable LLM if key missing)

To change default model without env var: edit `DEFAULT_MODEL` in `config.py`.

Domain Expertise Integration:

- Load per-agent domain prompts (e.g., regulatory compliance for finance / healthcare) via `agent.inject_domain_update()`.
- Periodically refresh knowledge from a curated knowledge base (policies, standards, historical sprint retros).
- Track a knowledge version tag in outputs for audit.

Workflow Orchestration:

- Introduce an event bus (e.g., simple pub/sub) so agents emit events: `PLAN_CREATED`, `BLOCKER_ADDED`, `RELEASE_DRAFTED`.
- Define escalation policy: blocker with risk=high -> notify human lead; unresolved after 2 iterations -> open JIRA ticket automatically.
- Persist an immutable audit log (JSON lines) for compliance & post-mortems.

Customer Experience Focus:

- Stakeholder communicator enforces plain-language readability score (e.g., target Flesch > 60).
- Add a sentiment / tone normalizer to avoid alarmist phrasing while still surfacing risk.
- Provide consistent field ordering & headings across all communication templates.

Data Integration:

- Planned connectors: velocity DB, incident tracker, CI/CD deployment stats API.
- Real-time injection: before release drafting, pull latest deployment freeze windows.
- Enforce data minimization: only include aggregated metrics in stakeholder reports.

Continuous Learning:

- Collect feedback signals: Was estimate accurate? Were blockers predicted? Was release delayed?
- Maintain per-task outcome annotations to refine future point estimation heuristics.
- Schedule weekly model / prompt review; version prompts with semantic diff tracking.

## Roadmap (Suggested Iterations)

1. Replace stubs with real `pyautogen` agents & LLM backend.
2. Add retrieval augmentation for historical sprint analogies.
3. Implement risk scoring model (simple logistic regression on past task delays).
4. Integrate deployment API to auto-populate release notes with commit summaries.
5. Add CLI subcommands: `plan`, `release`, `summarize`, `simulate`.
6. Add unit tests for planner task generation edge cases.
7. Add optional web dashboard for live plan & risk visualization.

## Outputs

Standard run prints:

- Sprint Plan (with Aggregate Risk Score & mitigation tasks)
- Release Summary (window, milestone, notes)
- Stakeholder Summary (business language)
- (Autogen mode) Raw LLM outputs truncated to 400 chars each

## License

MIT (add a LICENSE file if distributing externally).
