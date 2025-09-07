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
        # Base template enhanced with type hints
        base_tasks = [
            ("Requirements Clarification", "analysis"),
            ("Architecture Draft", "design"),
            ("Data Model Design", "design"),
            ("Implementation", "feature"),
            ("Testing & QA", "quality"),
            ("Deployment Prep", "ops"),
        ]
        tasks = []
        risk_map = {"low": 1, "medium": 3, "high": 6}
        default_business_value = 8
        default_time_criticality = 5
        default_risk_reduction = 3
        for i, (t, t_type) in enumerate(base_tasks, start=1):
            risk = "medium" if i in (4, 5) else "low"
            estimate = 8 if t == "Implementation" else 3
            prob = 0.2 if risk == "low" else 0.4
            impact = 2 if risk == "low" else 4
            exposure = prob * impact * estimate
            wsjf = (default_business_value + default_time_criticality + default_risk_reduction) / max(estimate, 1)
            tasks.append({
                "id": f"T{i}",
                "title": f"{t} ({initiative[:30]})",
                "type": t_type,
                "estimate_points": estimate,
                "risk": risk,
                "risk_score": risk_map[risk] * estimate,
                "risk_probability": prob,
                "risk_impact": impact,
                "risk_exposure": exposure,
                "wsjf": round(wsjf, 2),
                "priority": i,  # initial ordering
                "acceptance": "TBD",
                "depends_on": [f"T{i-1}"] if i > 1 else [],
            })
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
            "type": "mitigation",
            "estimate_points": 2,
            "risk": "high",
            "risk_score": 2 * 6,
            "risk_probability": 0.5,
            "risk_impact": 5,
            "risk_exposure": 0.5 * 5 * 2,
            "wsjf": round((5 + 5 + 5) / 2, 2),  # placeholder scoring for mitigation
            "priority": len(plan['tasks']) + 1,
            "acceptance": "Mitigation effective",
            "depends_on": [],
        }
        plan["tasks"].append(mitigation_task)
        plan["blockers"].append(blocker)
        plan["aggregate_risk_score"] = sum(t.get("risk_score", 0) for t in plan["tasks"])
        self.send(f"Added mitigation task for blocker: {blocker}")
        return plan

__all__ = ["SprintPlanner"]
