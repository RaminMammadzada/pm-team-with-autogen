"""Real Autogen integration layer.

Provides factory functions that return configured Autogen ConversableAgent instances
mirroring the roles implemented in the lightweight stubs. If Autogen import fails,
raises a clear error instructing the user to install dependencies / configure keys.
"""
from __future__ import annotations
from typing import Dict, Any
from .config import create_llm_config, describe_key_setup

try:
    from autogen import ConversableAgent  # type: ignore
except Exception as e:  # pragma: no cover
    raise ImportError(
        "Autogen package not available or failed to import. Ensure 'autogen' is installed and env vars set."
    ) from e


def _base_config(timeout: int = 60) -> Dict[str, Any]:
    llm_cfg = create_llm_config(timeout=timeout)
    return {
        "llm_config": llm_cfg,
        "human_input_mode": "NEVER",
    }


def create_sprint_planner() -> ConversableAgent:
    agent = ConversableAgent(
        name="SprintPlanner",
        system_message=(
            "You are the Sprint Planner. Break initiatives into structured tasks with IDs, "
            "story point estimates, risk level (low|medium|high), and dependencies. Provide JSON only."
        ),
        **_base_config(),
    )
    return agent


def create_release_coordinator() -> ConversableAgent:
    agent = ConversableAgent(
        name="ReleaseCoordinator",
        system_message=(
            "You are the Release Coordinator. Given sprint plan JSON, propose release window (dates), "
            "list notable tasks for release notes, and a concise rollback checklist. Output JSON only."
        ),
        **_base_config(),
    )
    return agent


def create_stakeholder_communicator() -> ConversableAgent:
    agent = ConversableAgent(
        name="StakeholderCommunicator",
        system_message=(
            "You translate technical sprint/release JSON into a business update. Include: initiative summary, "
            "total points, risks (grouped), next milestone. Plain concise prose under 120 words."
        ),
        **_base_config(),
    )
    return agent


def wire_autogen_team() -> Dict[str, ConversableAgent]:
    team = {
        "planner": create_sprint_planner(),
        "release": create_release_coordinator(),
        "stakeholder": create_stakeholder_communicator(),
    }
    # If llm_config is False, warn user once.
    if team["planner"].llm_config is False:
        print("[WARN] LLM disabled (no OPENAI_API_KEY). " + describe_key_setup())
    return team
