"""Real Autogen integration layer (import optional)."""
from __future__ import annotations
from typing import Dict, Any
from .config import create_llm_config, describe_key_setup

try:  # pragma: no cover - networked dependency
    from autogen import ConversableAgent  # type: ignore
except Exception as e:  # pragma: no cover
    raise ImportError(
        "Autogen not available. Install 'autogen' and set OPENAI_API_KEY to enable --autogen mode."
    ) from e


def _base_config(timeout: int = 60) -> Dict[str, Any]:
    return {"llm_config": create_llm_config(timeout=timeout), "human_input_mode": "NEVER"}


def create_sprint_planner() -> ConversableAgent:
    return ConversableAgent(
        name="SprintPlanner",
        system_message=(
            "You are the Sprint Planner. Break initiatives into structured tasks with IDs, "
            "story point estimates, risk level (low|medium|high), and dependencies. Provide JSON only."
        ),
        **_base_config(),
    )


def create_release_coordinator() -> ConversableAgent:
    return ConversableAgent(
        name="ReleaseCoordinator",
        system_message=(
            "You are the Release Coordinator. Given sprint plan JSON, propose release window (dates), "
            "list notable tasks for release notes, and a concise rollback checklist. Output JSON only."
        ),
        **_base_config(),
    )


def create_stakeholder_communicator() -> ConversableAgent:
    return ConversableAgent(
        name="StakeholderCommunicator",
        system_message=(
            "Translate plan/release JSON into a concise business update: initiative, total points, "
            "risks grouped, next milestone. Plain prose under 120 words."
        ),
        **_base_config(),
    )


def wire_autogen_team() -> Dict[str, ConversableAgent]:
    team = {
        "planner": create_sprint_planner(),
        "release": create_release_coordinator(),
        "stakeholder": create_stakeholder_communicator(),
    }
    if team["planner"].llm_config is False:
        print("[WARN] LLM disabled. " + describe_key_setup())
    return team

__all__ = ["wire_autogen_team"]
