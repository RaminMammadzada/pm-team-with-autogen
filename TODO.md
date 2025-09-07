# Enhancement Roadmap

Phased plan to evolve the stub planner into a richer, semi-realistic project management assistant.

## Phase 1 (Foundational Enrichment)

- [x] WSJF scoring (business value, time criticality, risk reduction, job size)
- [x] Add task fields: `type`, `priority`, `acceptance` placeholder
- [x] Risk model: probability & impact, exposure = prob _ impact _ points
- [ ] Velocity overrides via `PM_TEAM_VELOCITY`
- [ ] Sprint length override via `PM_TEAM_SPRINT_DAYS`
- [ ] Forecast (sprint count + estimated completion date) `--forecast`
- [ ] JSON schema validation for plan artifact (basic)

## Phase 2 (Delivery & Governance)

- [ ] Dependency graph (DAG) + critical path length
- [ ] Release readiness checklist with gating score
- [ ] Multi-role summaries (Exec, Eng, Compliance)
- [ ] Backlog reprioritization when exposure threshold exceeded
- [ ] Scenario: add/remove feature impact on delivery date

## Phase 3 (Analytics & Adaptation)

- [ ] Monte Carlo forecasting using historical throughput
- [ ] Historical metric persistence (velocity, lead time)
- [ ] Trend-based risk early warning agent
- [ ] Cost of delay & burn rate estimation

## Phase 4 (Intelligent Assistance)

- [ ] ML-based risk prediction (requires historical dataset)
- [ ] Adaptive estimation (Bayesian adjustment)
- [ ] LLM-assisted requirement to structured stories extraction
- [ ] Calendar integration for capacity accuracy

## Phase 5 (Operational Hardening)

- [ ] Concurrency-safe file locking
- [ ] Structured database (SQLite) for artifacts & metrics
- [ ] API service layer (FastAPI) for remote orchestration
- [ ] Angular UI integration layer (backlog board, risk heatmap)
- [ ] Event streaming (WebSocket) for live dashboard

## Backlog / Ideas

- [ ] Plugin system for custom scoring formulas
- [ ] SLA-based prioritization weight
- [ ] Integration with ticketing systems (Jira/GitHub placeholder)

---

Incremental implementation will tick these off with associated commit messages.
