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


def agent_reply(run_dir: Path, project: str, user_text: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Append a user message and generate an agent reply.

    Currently stateless instantiation each call; replays history into agent.
    """
    user_message = {"sender": "user", "content": user_text, "timestamp": _now_iso()}
    history = append_messages(run_dir, [user_message])

    # Build agent and replay
    agent = ConversableAgentBase(name="planning_agent", system_prompt="You are a planning assistant that provides concise, actionable responses.")
    for m in history:
        agent.receive(AgentMessage(sender=m['sender'], content=m['content'], timestamp=datetime.now(UTC)))
    reply_agent_msg = agent.respond(user_text)
    reply_message = {"sender": "agent", "content": reply_agent_msg.content, "timestamp": _now_iso()}
    history = append_messages(run_dir, [reply_message])
    return reply_message, history

__all__ = [
    "load_conversation",
    "append_messages",
    "agent_reply",
]
