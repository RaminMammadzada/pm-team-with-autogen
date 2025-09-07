from __future__ import annotations
from typing import Dict, Any
from datetime import datetime, timedelta, UTC
from .base import ConversableAgentBase, now_iso


class ReleaseCoordinator(ConversableAgentBase):
    def __init__(self):
        super().__init__(
            name="ReleaseCoordinator",
            system_prompt="Crafts release schedules, notes, and rollback templates from sprint data."
        )

    def draft_release(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        start = datetime.now(UTC) + timedelta(days=3)
        window = f"{start.date()} -> {(start + timedelta(days=2)).date()}"
        notes = [f"{t['id']}: {t['title']}" for t in plan['tasks']]
        summary = {
            "generated_at": now_iso(),
            "window": window,
            "next_milestone": (start + timedelta(days=7)).date().isoformat(),
            "notes": notes[:6],
            "rollback_stub": "If critical failure: 1) Notify stakeholders 2) Revert infra changes 3) Restore DB snapshot 4) Post-mortem",
        }
        self.send("Drafted release summary.")
        return summary
