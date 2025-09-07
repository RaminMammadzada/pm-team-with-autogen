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
from .autogen_agent import autogen_generate

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


def _use_autogen() -> bool:
    return os.getenv("USE_AUTOGEN", "0") in ("1", "true", "True")


def _force_llm() -> bool:
    """If set, disable heuristic fallback and require a real LLM key.

    FORCE_LLM=1 will cause queries to return a configuration error instead of
    heuristic content when OPENAI_API_KEY is missing.
    """
    return os.getenv("FORCE_LLM", "0") in ("1", "true", "True")


def _build_structured_context(run_dir: Path) -> Dict[str, Any]:
    """Provide a machine-consumable slice of artifacts (limited for tokens)."""
    plan = _load_artifact_json(run_dir, "plan.json") or {}
    tasks = plan.get("tasks", [])
    # Limit tasks to first 30 by priority/id to avoid token explosion
    tasks_sorted = sorted(tasks, key=lambda t: (t.get("priority", 9999), t.get("id", "")))[:30]
    reduced_tasks = [
        {
            "id": t.get("id"),
            "title": t.get("title"),
            "status": t.get("status"),
            "risk": t.get("risk"),
            "risk_score": t.get("risk_score"),
            "estimate_points": t.get("estimate_points"),
            "priority": t.get("priority"),
        }
        for t in tasks_sorted
    ]
    return {
        "initiative": plan.get("initiative"),
        "aggregate_risk_score": plan.get("aggregate_risk_score"),
        "velocity_assumption": plan.get("velocity_assumption"),
        "blockers": plan.get("blockers", []),
        "tasks": reduced_tasks,
    }


def _llm_chat_completion(domain_summary: str, history: List[Dict[str, Any]], user_text: str) -> str:
    """Call OpenAI Chat Completion API with trimmed history.

    Falls back by raising on any exception for outer handler to catch.
    """
    client = OpenAI()  # api key picked up from env
    model = os.getenv("PM_TEAM_LLM_MODEL") or os.getenv("OPENAI_MODEL_NAME") or "gpt-4o-mini"
    # Trim last 12 messages (user+agent) for context
    recent = history[-12:]
    msgs = []
    # Build structured context JSON for richer grounding (lightweight slice)
    # We embed as fenced JSON so model can parse reliably.
    from json import dumps as _dumps
    structured = _build_structured_context(Path(history[0].get("run_dir", ".")) if history else Path("."))
    system_instructions = (
        "You are an expert agile planning assistant. Provide concise, actionable responses grounded ONLY in the supplied artifacts. "
        "If the user asks: status/progress -> produce a brief snapshot (task count, points, high risk count, blockers, est sprints). "
        "If mitigation or reprioritization is requested -> list concrete steps referencing task IDs. "
        "NEVER invent tasks or blockers not present. If insufficient info, ask a clarifying question. "
        "Prefer bullet lists for multi-step guidance; otherwise a short paragraph."
    )
    combined_context = (
        system_instructions
        + "\n\nTEXT_SUMMARY:\n" + domain_summary
        + "\n\nSTRUCTURED_CONTEXT (JSON):\n```json\n" + _dumps(structured, ensure_ascii=False) + "\n```"
    )
    msgs.append({"role": "system", "content": combined_context})
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
    is_status_query = any(k in user_text.lower() for k in ["what is happening", "status", "summary", "progress", "update"])

    if _force_llm() and not _llm_available():
        # Explicit configuration error path
        reply_message = {
            "sender": "agent",
            "content": (
                "Configuration error: FORCE_LLM is enabled but OPENAI_API_KEY is not set. "
                "Please provide an API key to get LLM-backed answers."
            ),
            "timestamp": _now_iso(),
        }
        history = append_messages(run_dir, [reply_message])
        return reply_message, history

    if _use_autogen() and _llm_available():
        try:
            reply_text = autogen_generate(domain_summary, history, user_text)
        except Exception:
            # Fall through to direct LLM attempt
            if _llm_available():
                try:
                    reply_text = _llm_chat_completion(domain_summary, history, user_text)
                except Exception:
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
    elif _llm_available():
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
        base_reply = agent.respond(user_text).content
        # Suppress noisy environment hint for common status queries to keep UX clean
        if is_status_query:
            reply_text = base_reply
        else:
            reply_text = base_reply + "\n(Set OPENAI_API_KEY for LLM responses)"

    reply_message = {"sender": "agent", "content": reply_text, "timestamp": _now_iso()}
    history = append_messages(run_dir, [reply_message])
    return reply_message, history

__all__ = [
    "load_conversation",
    "append_messages",
    "agent_reply",
]
