from __future__ import annotations
from typing import Dict, Any
from .base import ConversableAgentBase, now_iso


class SprintPlanner(ConversableAgentBase):
    def __init__(self):
        super().__init__(
            name="SprintPlanner",
            system_prompt="Break initiatives into sprint-sized, estimable tasks with risks and dependencies.",
        )

    def plan(self, initiative: str) -> Dict[str, Any]:
        base_tasks = [
            "Requirements Clarification",
            "Architecture Draft",
            "Data Model Design",
            "Implementation",
            "Testing & QA",
            "Deployment Prep",
        ]
        tasks = []
        risk_map = {"low": 1, "medium": 3, "high": 6}
        for i, t in enumerate(base_tasks, start=1):
            risk = "medium" if i in (4, 5) else "low"
            estimate = 3 if i not in (4,) else 8
            tasks.append(
                {
                    "id": f"T{i}",
                    "title": f"{t} ({initiative[:30]})",
                    "estimate_points": estimate,
                    "risk": risk,
                    "risk_score": risk_map[risk] * estimate,
                    "depends_on": [f"T{i-1}"] if i > 1 else [],
                }
            )
        aggregate_risk = sum(t["risk_score"] for t in tasks)
        plan = {
            "initiative": initiative,
            "generated_at": now_iso(),
            "sprint_goal": f"Deliver foundation for: {initiative[:60]}",
            "velocity_assumption": 30,
            "tasks": tasks,
            "blockers": [],
            "aggregate_risk_score": aggregate_risk,
        }
        self.send(f"Produced sprint plan with {len(tasks)} tasks.")
        return plan

    def refine_for_blocker(self, plan: Dict[str, Any], blocker: str) -> Dict[str, Any]:
        mitigation_task = {
            "id": f"M{len(plan['tasks'])+1}",
            "title": f"Mitigate blocker: {blocker[:40]}",
            "estimate_points": 2,
            "risk": "high",
            "risk_score": 2 * 6,
            "depends_on": [],
        }
        plan["tasks"].append(mitigation_task)
        plan["blockers"].append(blocker)
        plan["aggregate_risk_score"] = sum(t.get("risk_score", 0) for t in plan["tasks"])
        self.send(f"Added mitigation task for blocker: {blocker}")
        return plan

__all__ = ["SprintPlanner"]
