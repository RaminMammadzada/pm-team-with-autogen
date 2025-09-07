from __future__ import annotations
from typing import Dict, Any
from .base import ConversableAgentBase


class StakeholderCommunicator(ConversableAgentBase):
    def __init__(self):
        super().__init__(
            name="StakeholderCommunicator",
            system_prompt="Translate sprint data into concise, risk-aware business updates.",
        )

    def summarize(self, plan: Dict[str, Any], release_summary: Dict[str, Any]) -> str:
        total_points = sum(t["estimate_points"] for t in plan["tasks"])
        risks = [t for t in plan["tasks"] if t["risk"] != "low"]
        risk_line = ", ".join(f"{t['id']}({t['risk']})" for t in risks) or "None"
        msg = (
            f"Initiative: {plan['initiative']}. Total tasks: {len(plan['tasks'])}, Total points: {total_points}. "
            f"Planned Release Window: {release_summary['window']} | Risks: {risk_line}. "
            f"Next milestone: {release_summary['next_milestone']}"
        )
        self.send("Generated stakeholder summary.")
        return msg

__all__ = ["StakeholderCommunicator"]
