from __future__ import annotations
from typing import Dict, Any, Optional, List, Callable
import json
from datetime import datetime, UTC
from .sprint_planner import SprintPlanner
from .stakeholder_communicator import StakeholderCommunicator
from .release_coordinator import ReleaseCoordinator


class EventBus:
    """Very small synchronous event bus."""

    def __init__(self):
        self._subs: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self.history: List[Dict[str, Any]] = []

    def subscribe(self, event: str, handler: Callable[[Dict[str, Any]], None]):
        self._subs.setdefault(event, []).append(handler)

    def emit(self, event: str, payload: Dict[str, Any]):
        record = {"event": event, "timestamp": datetime.now(UTC).isoformat(), "payload": payload}
        self.history.append(record)
        for h in self._subs.get(event, []):
            h(payload)


class AuditLogger:
    """Append-only JSONL audit logger with optional size-based rotation.

    Rotation: If env PM_TEAM_AUDIT_MAX_BYTES is set (int) and file exceeds that size after a write,
    it's renamed to audit_log.<timestamp>.jsonl and a fresh file is started.
    """

    def __init__(self, path: str = "audit_log.jsonl"):
        self.path = path

    def _maybe_rotate(self):
        import os
        max_bytes = os.getenv("PM_TEAM_AUDIT_MAX_BYTES")
        if not max_bytes:
            return
        try:
            limit = int(max_bytes)
        except ValueError:
            return
        try:
            size = os.path.getsize(self.path)
        except OSError:
            return
        if size <= limit:
            return
        # rotate
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        rotated = f"{self.path.rsplit('.jsonl', 1)[0]}.{ts}.jsonl"
        try:
            os.replace(self.path, rotated)
        except OSError:
            pass

    def log(self, event: str, data: Dict[str, Any]):
        line = json.dumps({"event": event, "at": datetime.now(UTC).isoformat(), **data}, ensure_ascii=False)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        self._maybe_rotate()


class MetricsAccumulator:
    def __init__(self):
        self.counters: Dict[str, int] = {"plans_created": 0, "blockers_recorded": 0}
        self.last_points: int = 0

    def incr(self, key: str, amount: int = 1):
        self.counters[key] = self.counters.get(key, 0) + amount

    def snapshot(self) -> Dict[str, Any]:
        return {**self.counters, "last_points": self.last_points}


class PMTeamOrchestrator:
    def __init__(self, audit_path: str = "audit_log.jsonl"):
        self.sprint = SprintPlanner()
        self.release = ReleaseCoordinator()
        self.comm = StakeholderCommunicator()
        self.bus = EventBus()
        self.audit = AuditLogger(audit_path)
        self.metrics = MetricsAccumulator()
        # Register audit mirroring
        self.bus.subscribe("PLAN_CREATED", lambda p: self.audit.log("PLAN_CREATED", {"task_count": len(p['tasks'])}))
        self.bus.subscribe("BLOCKER_ADDED", lambda p: self.audit.log("BLOCKER_ADDED", {"blocker": p['blocker']}))
        self.bus.subscribe("RELEASE_DRAFTED", lambda p: self.audit.log("RELEASE_DRAFTED", {"window": p['window']}))
        self.bus.subscribe("STAKEHOLDER_SUMMARY", lambda p: self.audit.log("STAKEHOLDER_SUMMARY", {"length": len(p['summary'])}))

    def run(self, initiative: str, blocker: Optional[str] = None, blockers: Optional[List[str]] = None) -> Dict[str, Any]:
        plan = self.sprint.plan(initiative)
        self.metrics.incr("plans_created")
        total_points = sum(t["estimate_points"] for t in plan["tasks"])
        self.metrics.last_points = total_points
        self.bus.emit("PLAN_CREATED", {"initiative": initiative, "tasks": plan["tasks"]})
        collected_blockers: List[str] = []
        if blocker:
            collected_blockers.append(blocker)
        if blockers:
            collected_blockers.extend(blockers)
        for b in collected_blockers:
            plan = self.sprint.refine_for_blocker(plan, b)
            self.metrics.incr("blockers_recorded")
            self.bus.emit("BLOCKER_ADDED", {"blocker": b})
        release_view = self.release.draft_release(plan)
        self.bus.emit("RELEASE_DRAFTED", release_view)
        stakeholder_summary = self.comm.summarize(plan, release_view)
        self.bus.emit("STAKEHOLDER_SUMMARY", {"summary": stakeholder_summary})
        result = {
            "plan": plan,
            "release": release_view,
            "stakeholder_summary": stakeholder_summary,
            "metrics": self.metrics.snapshot(),
            "aggregate_risk_score": plan.get("aggregate_risk_score"),
        }
        self.audit.log("RUN_COMPLETED", {"initiative": initiative, "points": total_points})
        return result

__all__ = ["PMTeamOrchestrator", "EventBus", "AuditLogger", "MetricsAccumulator"]
