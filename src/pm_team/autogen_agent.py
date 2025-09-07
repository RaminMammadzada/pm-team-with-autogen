from __future__ import annotations
"""Autogen multi-agent helpers.

Provides a thin wrapper so the rest of the app does not depend directly on
Autogen APIs. We keep usage minimal (single assistant) for now to avoid
unnecessary complexity. Future: introduce Planner/Critic loop.
"""
from typing import List, Dict
import os

_DEFAULT_MODEL = "gpt-4o-mini"


def _get_llm_config():
    model = os.getenv("PM_TEAM_LLM_MODEL", _DEFAULT_MODEL)
    # Autogen expects a config_list under llm_config
    return {
        "config_list": [
            {
                "model": model,
                # Rely on OPENAI_API_KEY in env (Autogen/OpenAI SDK picks it up)
            }
        ],
        "temperature": 0.3,
        "timeout": 60,
    }


def autogen_generate(domain_summary: str, history: List[Dict], user_text: str) -> str:
    """Generate a reply using Autogen's AssistantAgent.

    History is a list of {sender, content}. We fold a trimmed slice into
    the prompt rather than replaying the whole chat to keep token usage low.
    """
    try:
        from autogen import AssistantAgent, UserProxyAgent  # type: ignore
    except Exception as e:  # pragma: no cover - import guard
        raise RuntimeError(f"Autogen import failed: {e}")

    trimmed = history[-10:]
    recent_lines = [f"[{m['sender']}] {m['content']}" for m in trimmed]
    recent_block = "\n".join(recent_lines)
    system_msg = (
        "You are an expert agile / program planning assistant. Provide concise, actionable answers. "
        "Reference task IDs where relevant. If user asks for status, summarize task count, high risk tasks, blockers, points and estimated sprints. "
        "Never invent tasks not in the plan. If clarification is needed, ask a short follow-up question.\n\nPLAN_CONTEXT:\n" + domain_summary
    )
    llm_config = _get_llm_config()

    assistant = AssistantAgent(
        name="planner_assistant",
        system_message=system_msg,
        llm_config=llm_config,
    )
    user_proxy = UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        code_execution_config={"use_docker": False},  # disable code exec
    )

    # Compose the user prompt including recent context
    composite_prompt = (
        f"RECENT_MESSAGES:\n{recent_block}\n\nUSER_QUERY:\n{user_text}\n\nRespond now." if recent_block else user_text
    )

    # Initiate single-turn chat (we cap to 1 assistant response)
    user_proxy.initiate_chat(
        assistant,
        message=composite_prompt,
        max_turns=1,
    )

    # Extract last assistant message
    msgs = assistant.chat_messages.get(assistant, [])
    if not msgs:
        raise RuntimeError("No response from Autogen assistant")
    # Messages are dicts with 'content'
    for m in reversed(msgs):
        content = m.get("content")
        if content:
            return content.strip()
    return "(Empty response)"

__all__ = ["autogen_generate"]
