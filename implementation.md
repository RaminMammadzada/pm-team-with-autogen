# Interactive Initiative Refinement & Conversational Agent Integration

This document details the design and implementation plan to evolve the current PM Team prototype from one‑shot initiative generation into an interactive, explainable, iterative planning workspace powered by a lightweight `ConversableAgentBase`.

---

## 1. Objectives

1. Add persistent initiative conversation history (per run / initiative).
2. Expose backend chat endpoints for retrieving and extending the conversation.
3. Provide a frontend chat panel tied to the currently selected initiative.
4. Allow users to ask for refinements, explanations, or risk/priority adjustments (initially advisory only).
5. Lay groundwork for future artifact mutation (producing versioned plans or diffs) without breaking compatibility.

---

## 2. Current State (Baseline)

- Initiatives ("runs") are generated once via `POST /projects/{slug}/runs` using `PMTeamOrchestrator`.
- Artifacts (plan.json, metrics.json, etc.) are persisted under `outputs/<project>/<timestamp_slug>/`.
- No conversational or iterative refinement channel exists.
- `ConversableAgentBase` stub provides:
  - Conversation history (in-memory per process)
  - `respond()` naive heuristic reply
  - Domain knowledge append capability

---

## 3. High-Level Architecture Additions

| Component            | Responsibility                                                    | Persistence                                     |
| -------------------- | ----------------------------------------------------------------- | ----------------------------------------------- |
| Conversation Storage | Append-only list of `{sender, content, timestamp}` per initiative | `conversation.json`                             |
| Chat API             | REST endpoints to fetch & extend conversation                     | FastAPI (`/chat` routes)                        |
| Agent Wrapper        | Load prior messages; generate agent response                      | `ConversableAgentBase`                          |
| Frontend Chat Panel  | Display messages + input box; optimistic append                   | Angular (extend root component for first slice) |

---

## 4. Data Model

### 4.1 Conversation Message JSON Schema

```jsonc
{
  "sender": "user" | "agent",
  "content": "string (markdown/plain)",
  "timestamp": "ISO-8601"
}
```

Stored as an array in `outputs/<project>/<run_id>/conversation.json`.

### 4.2 API Payloads

1. `GET /projects/{slug}/runs/{run_id}/chat`
   - Response: `{ "messages": Message[] }`
2. `POST /projects/{slug}/runs/{run_id}/chat`
   - Request: `{ "message": "text" }`
   - Response: `{ "messages": Message[], "reply": Message }`

(Extensible later with `mode`, e.g. `"refine_plan" | "explain_task"`).

---

## 5. Backend Changes

### 5.1 New Module: `conversation.py`

Functions:

- `load_conversation(run_dir: Path) -> list[dict]`
- `append_messages(run_dir: Path, new: list[dict]) -> list[dict]` (returns full list)
- `agent_reply(run_dir: Path, project: str, user_text: str) -> (reply_message: dict, full_history: list[dict])`
  - Instantiates `ConversableAgentBase` each call (stateless across requests except file persistence)
  - Replays prior messages into agent history
  - Sends user message, then calls `respond()` to generate agent message

### 5.2 API Additions (in `api.py`)

Routes:

- `GET /projects/{slug}/runs/{run_id}/chat`
- `POST /projects/{slug}/runs/{run_id}/chat`
  Error Handling:
- 404 if run directory missing
- 400 if message empty

### 5.3 Security / Limits

Initial prototype: no auth, no rate limiting. Later improvements:

- Max conversation length trimming (keep last N=200 messages)
- Simple size guard (truncate huge user inputs > 4000 chars)

### 5.4 Future Mutation Path (Not Implemented Now)

Add `mode` field to POST enabling plan refinement path:

- `mode = "refine"` -> produce `plan_v2.json` and store diff.
- Diff stored as `plan_diff_v1_v2.json`.
  This requires orchestrator re-run with modified initiative context; deferred until baseline chat stable.

---

## 6. Frontend Changes

### 6.1 Service Extensions (`data.service.ts`)

Add methods:

- `getChat(slug: string, runId: string)` → Observable<{messages: Message[]}>
- `sendChat(slug: string, runId: string, message: string)` → Observable<{messages: Message[], reply: Message}>

Message interface:

```ts
export interface ChatMessage {
  sender: string;
  content: string;
  timestamp: string;
}
```

### 6.2 UI Slice (First Iteration)

- Add a `conversation` panel under Plan section (collapsible later).
- Show messages in scrollable column.
- Input + send button (disabled while awaiting reply / empty).
- Optimistic append user message while awaiting response; replace with canonical server payload when returned.

### 6.3 State Additions (in `app.ts`)

Signals:

- `chatMessages = signal<ChatMessage[]>([])`
- `chatLoading = signal(false)`
- `chatSending = signal(false)`
  Methods:
- `loadChat()` called when selecting run
- `sendChat()` handles optimistic push & service call

### 6.4 Basic Styling (`app.scss`)

Add `.chat-panel` container with max-height and internal scroll for messages.
Message alignment variant for `user` vs `agent`.

---

## 7. Versioning & Backward Compatibility

- No change to existing artifact schema (plan / metrics unaffected).
- New file `conversation.json` optional; absence implies empty history.
- API additions are additive; no breaking changes.

---

## 8. Observability / Audit

- (Future) Mirror chat events to `audit_log.jsonl` with event type `CHAT_USER` and `CHAT_AGENT`.
- Not in first slice to keep diff small.

---

## 9. Edge Cases & Handling

| Case              | Strategy                                     |
| ----------------- | -------------------------------------------- |
| Empty message     | 400 reject                                   |
| Oversized message | Truncate server-side (log) – later enforce   |
| Concurrent sends  | Frontend disables button while `chatSending` |
| Missing run       | 404                                          |
| Corrupted JSON    | Reinitialize conversation file               |

---

## 10. Testing Strategy (Minimal for First Slice)

- Unit-ish manual test via curl: POST then GET confirm append order.
- Frontend interaction: send a prompt, see response appear, persists after reload.
  (Full automated tests deferred.)

---

## 11. Phased Implementation

| Phase | Deliverables                                                    |
| ----- | --------------------------------------------------------------- |
| 1     | `implementation.md`, backend conversation module, API endpoints |
| 2     | Frontend service + minimal UI panel                             |
| 3     | Optimistic UI improvements + styling                            |
| 4     | (Future) Explain task / refine plan modes                       |
| 5     | (Future) Versioned plan artifacts & diff view                   |

Current PR / commit will cover Phase 1 + start of Phase 2.

---

## 12. Future Enhancements (Backlog)

- Multi-mode prompts (explain, risk_reduce, reprioritize)
- Plan versioning & diff visualizer
- Streaming responses (Server-Sent Events)
- Multi-agent (RiskAgent, ReleaseAgent) orchestrated via shared conversation file
- Embedding-based context summarization for long histories
- Auth & rate limiting

---

## 13. Acceptance Criteria (Phase 1 & 2)

| ID  | Description                                             | Status Metric                      |
| --- | ------------------------------------------------------- | ---------------------------------- |
| AC1 | GET chat returns empty list on new run                  | 200 + `{messages: []}`             |
| AC2 | POST chat with message persists both user + agent reply | Subsequent GET length = 2 more     |
| AC3 | Frontend displays conversation and allows sending       | UI shows messages; reload persists |
| AC4 | No regression in existing initiative generation         | Existing endpoints still 200       |

---

## 14. Risks

- Agent stateless reconstruction each call can be slow once logic grows (acceptable now).
- File corruption on concurrent writes (low likelihood with single-user dev; mitigate later with file lock or append log + periodic compaction).
- Chat panel cluttering UI (can be collapsible in later iteration).

---

## 15. Initial API Examples

```bash
# Send a message
curl -X POST localhost:8000/projects/insurance_claims/runs/20250907_123000_claim_processing/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Explain prioritization."}'

# Get conversation
curl localhost:8000/projects/insurance_claims/runs/20250907_123000_claim_processing/chat
```

---

## 16. Implementation Notes

- Keep first slice deliberately small to enable rapid iteration & user feedback on value before investing in refinement modes.
- Avoid premature abstraction; conversation logic intentionally simple.

---

End of design.
