from __future__ import annotations
"""Conversation persistence and agent integration.

Stores a simple array of messages in conversation.json under a run directory.
Each message: {"sender": "user"|"agent", "content": str, "timestamp": ISO8601}
"""
from pathlib import Path
from typing import List, Dict, Any, Tuple
import json
from datetime import datetime, UTC
from .base import ConversableAgentBase, Message as AgentMessage
import math
import os
from openai import OpenAI

CONVO_FILENAME = "conversation.json"


def _file(run_dir: Path) -> Path:
    return run_dir / CONVO_FILENAME


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def load_conversation(run_dir: Path) -> List[Dict[str, Any]]:
    fp = _file(run_dir)
    if not fp.exists():
        return []
    try:
        data = json.loads(fp.read_text())
        if isinstance(data, list):
            return [m for m in data if isinstance(m, dict) and 'sender' in m and 'content' in m]
    except Exception:
        pass
    # Corrupted -> reset
    return []


def _write(run_dir: Path, messages: List[Dict[str, Any]]):
    fp = _file(run_dir)
    try:
        fp.write_text(json.dumps(messages, indent=2, ensure_ascii=False))
    except Exception:
        # swallow write errors (future: log)
        pass


def append_messages(run_dir: Path, new_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    history = load_conversation(run_dir)
    history.extend(new_messages)
    # Trim if unbounded growth (keep last 500 for now)
    if len(history) > 500:
        history = history[-500:]
    _write(run_dir, history)
    return history


def _load_artifact_json(run_dir: Path, name: str) -> Any:
    p = run_dir / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _build_domain_summary(run_dir: Path) -> str:
    plan = _load_artifact_json(run_dir, "plan.json") or {}
    release = _load_artifact_json(run_dir, "release.json") or {}
    metrics = _load_artifact_json(run_dir, "metrics.json") or {}
    initiative = plan.get("initiative") or (run_dir.name.split("_", 1)[-1])
    tasks = plan.get("tasks", [])
    blockers = plan.get("blockers", [])
    agg_risk = plan.get("aggregate_risk_score")
    total_points = sum(t.get("estimate_points", 0) for t in tasks) if tasks else 0
    high_risk = [t for t in tasks if t.get("risk") == "high" or (t.get("risk_score", 0) >= 18)]
    # Sort tasks by priority (fallback to id)
    tasks_sorted = sorted(tasks, key=lambda t: (t.get("priority", 9999), t.get("id", "")))
    top_lines = [f"  - {t.get('id')}: {t.get('title')} (risk={t.get('risk')}, pts={t.get('estimate_points')})" for t in tasks_sorted[:10]]
    summary_lines = [
        f"INITIATIVE: {initiative}",
        f"TASK_COUNT: {len(tasks)}",
        f"TOTAL_POINTS: {total_points}",
        f"AGG_RISK: {agg_risk}",
        f"HIGH_RISK_TASKS: {len(high_risk)}",
        f"BLOCKERS: {', '.join(blockers) if blockers else 'None'}",
        "TOP_TASKS:",
        *top_lines,
    ]
    # Basic metrics augmentation (if present)
    if metrics:
        velocity = metrics.get("velocity") or metrics.get("velocity_assumption") or plan.get("velocity_assumption")
        if velocity:
            sprints = math.ceil(total_points / max(velocity, 1)) if total_points else 0
            summary_lines.append(f"EST_SPRINTS: {sprints}")
    if release:
        rel_notes = release.get("release_notes") or []
        summary_lines.append(f"RELEASE_ITEMS: {len(rel_notes)}")
    return "\n".join(l for l in summary_lines if l is not None)


def _llm_available() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def _llm_chat_completion(domain_summary: str, history: List[Dict[str, Any]], user_text: str) -> str:
    """Call OpenAI Chat Completion API with trimmed history.

    Falls back by raising on any exception for outer handler to catch.
    """
    client = OpenAI()  # api key picked up from env
    model = os.getenv("PM_TEAM_LLM_MODEL", "gpt-4o-mini")
    # Trim last 12 messages (user+agent) for context
    recent = history[-12:]
    msgs = []
    system_instructions = (
        "You are an expert agile planning assistant. Provide concise, actionable responses. "
        "Ground every answer in the provided plan context. If user asks for status, summarize tasks, risk, blockers. "
        "If user asks vague question like 'what is happening', produce a project status snapshot (tasks count, high risk tasks, blockers, estimate sprints). "
        "If risk mitigation or reprioritization is requested, outline concrete steps referencing task IDs. "
        "Never hallucinate tasks that aren't in context. If unsure, ask for clarification briefly."
    )
    msgs.append({"role": "system", "content": system_instructions + "\n\nPLAN_CONTEXT:\n" + domain_summary})
    for m in recent:
        role = "assistant" if m["sender"] == "agent" else "user"
        msgs.append({"role": role, "content": m["content"]})
    msgs.append({"role": "user", "content": user_text})
    try:
        resp = client.chat.completions.create(model=model, messages=msgs, temperature=0.3, max_tokens=400)
        content = resp.choices[0].message.content or "(no content returned)"
        return content.strip()
    except Exception as e:
        raise RuntimeError(f"LLM call failed: {e}")


def agent_reply(run_dir: Path, project: str, user_text: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Append a user message and generate an agent reply.

    Prefers real LLM (OpenAI) if OPENAI_API_KEY set; otherwise heuristic fallback.
    """
    user_message = {"sender": "user", "content": user_text, "timestamp": _now_iso()}
    history = append_messages(run_dir, [user_message])
    domain_summary = _build_domain_summary(run_dir)

    reply_text: str
    if _llm_available():
        try:
            reply_text = _llm_chat_completion(domain_summary, history, user_text)
        except Exception:
            # Silent fallback (could log) to heuristic agent
            agent = ConversableAgentBase(
                name="planning_agent",
                system_prompt="Heuristic fallback planning assistant.",
                domain_knowledge=domain_summary,
            )
            for m in history:
                agent.receive(AgentMessage(sender=m['sender'], content=m['content'], timestamp=datetime.now(UTC)))
            reply_text = agent.respond(user_text).content + "\n(Fallback used)"
    else:
        agent = ConversableAgentBase(
            name="planning_agent",
            system_prompt="Heuristic planning assistant (no OPENAI_API_KEY present).",
            domain_knowledge=domain_summary,
        )
        for m in history:
            agent.receive(AgentMessage(sender=m['sender'], content=m['content'], timestamp=datetime.now(UTC)))
        reply_text = agent.respond(user_text).content + "\n(Set OPENAI_API_KEY for LLM responses)"

    reply_message = {"sender": "agent", "content": reply_text, "timestamp": _now_iso()}
    history = append_messages(run_dir, [reply_message])
    return reply_message, history

__all__ = [
    "load_conversation",
    "append_messages",
    "agent_reply",
]
