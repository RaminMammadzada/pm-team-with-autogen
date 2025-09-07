from __future__ import annotations
"""Plan mutation utilities used by chat actions.

These functions operate directly on the persisted `plan.json` within a run
directory. They are intentionally conservative and deterministic.
"""
from pathlib import Path
from typing import Dict, Any, List
import json
from datetime import datetime, UTC


def _plan_path(run_dir: Path) -> Path:
    return run_dir / "plan.json"


def load_plan(run_dir: Path) -> Dict[str, Any]:
    p = _plan_path(run_dir)
    if not p.exists():
        raise FileNotFoundError("plan.json not found")
    return json.loads(p.read_text())


def save_plan(run_dir: Path, plan: Dict[str, Any]):
    p = _plan_path(run_dir)
    plan["updated_at"] = datetime.now(UTC).isoformat()
    p.write_text(json.dumps(plan, indent=2, ensure_ascii=False))


def add_blocker_task(run_dir: Path, blocker: str) -> Dict[str, Any]:
    plan = load_plan(run_dir)
    tasks: List[Dict[str, Any]] = plan.get("tasks", [])
    next_idx = len(tasks) + 1
    mitigation_task = {
        "id": f"M{next_idx}",
        "title": f"Mitigate blocker: {blocker[:40]}",
        "type": "mitigation",
        "estimate_points": 2,
        "risk": "high",
        "risk_score": 12,  # 2 points * risk weight 6
        "risk_probability": 0.5,
        "risk_impact": 5,
        "risk_exposure": 0.5 * 5 * 2,
        "wsjf": 7.5,
        "priority": next_idx,
        "acceptance": "Mitigation effective",
        "depends_on": [],
    }
    tasks.append(mitigation_task)
    plan.setdefault("blockers", []).append(blocker)
    plan["aggregate_risk_score"] = sum(t.get("risk_score", 0) for t in tasks)
    save_plan(run_dir, plan)
    return plan


def reprioritize_tasks(run_dir: Path, ordered_ids: List[str]) -> Dict[str, Any]:
    plan = load_plan(run_dir)
    tasks: List[Dict[str, Any]] = plan.get("tasks", [])
    # Build lookup
    by_id = {t.get("id"): t for t in tasks if t.get("id")}
    # Filter provided list to existing unique IDs
    normalized = []
    seen = set()
    for tid in ordered_ids:
        if tid in by_id and tid not in seen:
            normalized.append(tid)
            seen.add(tid)
    # Remaining tasks preserving original order
    remaining = [t.get("id") for t in tasks if t.get("id") not in seen]
    final_order = normalized + remaining
    # Reassign priorities sequentially
    for idx, tid in enumerate(final_order, start=1):
        by_id[tid]["priority"] = idx
    # Sort tasks list by new priority
    tasks.sort(key=lambda t: t.get("priority", 9999))
    save_plan(run_dir, plan)
    return plan

__all__ = ["add_blocker_task", "reprioritize_tasks", "load_plan", "save_plan"]
from typing import Mapping


def update_task_statuses(run_dir: Path, status_map: Mapping[str, str]) -> Dict[str, Any]:
    """Update status field for tasks whose IDs appear in status_map.

    status_map values are normalized to lowercase single tokens where possible.
    Returns updated plan.
    """
    plan = load_plan(run_dir)
    tasks: List[Dict[str, Any]] = plan.get("tasks", [])
    norm = {k.strip(): v.strip() for k, v in status_map.items() if k and v}
    changed = False
    for t in tasks:
        tid = t.get("id")
        if tid in norm:
            new_status = norm[tid]
            if t.get("status") != new_status:
                t["status"] = new_status
                changed = True
    if changed:
        plan["updated_at"] = datetime.now(UTC).isoformat()  # type: ignore[name-defined]
        save_plan(run_dir, plan)
    return plan

__all__.append("update_task_statuses")
