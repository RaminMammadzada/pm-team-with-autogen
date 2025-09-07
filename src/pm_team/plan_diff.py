from __future__ import annotations
"""Utilities to compute differences between two plan objects.

Produces a concise JSON-serializable structure with added/removed/modified tasks
and aggregate risk delta.
"""
from typing import Dict, Any, List

TASK_FIELDS_OF_INTEREST = [
    "title",
    "priority",
    "estimate_points",
    "risk",
    "risk_score",
    "wsjf",
    "risk_probability",
    "risk_impact",
    "risk_exposure",
    "type",
    "depends_on",
]


def _task_index(tasks: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for t in tasks:
        tid = t.get("id")
        if isinstance(tid, str) and tid:
            out[tid] = t
    return out


def diff_plans(old: Dict[str, Any] | None, new: Dict[str, Any] | None) -> Dict[str, Any]:
    if not old and not new:
        return {"added": [], "removed": [], "modified": []}
    old_tasks = (old or {}).get("tasks", [])
    new_tasks = (new or {}).get("tasks", [])
    old_idx = _task_index(old_tasks)
    new_idx = _task_index(new_tasks)
    added = []
    removed = []
    modified = []
    for tid, task in new_idx.items():
        if tid not in old_idx:
            added.append(task)
    for tid, task in old_idx.items():
        if tid not in new_idx:
            removed.append(task)
    for tid in set(old_idx.keys()).intersection(new_idx.keys()):
        o = old_idx[tid]
        n = new_idx[tid]
        changes = {}
        for f in TASK_FIELDS_OF_INTEREST:
            ov = o.get(f)
            nv = n.get(f)
            if ov != nv:
                changes[f] = {"old": ov, "new": nv}
        if changes:
            modified.append({"id": tid, "changes": changes})
    agg_old = (old or {}).get("aggregate_risk_score")
    agg_new = (new or {}).get("aggregate_risk_score")
    return {
        "added": added,
        "removed": removed,
        "modified": modified,
        "aggregate_risk_old": agg_old,
        "aggregate_risk_new": agg_new,
        "aggregate_risk_delta": (agg_new - agg_old) if (isinstance(agg_new, (int, float)) and isinstance(agg_old, (int, float))) else None,
    }

__all__ = ["diff_plans"]
