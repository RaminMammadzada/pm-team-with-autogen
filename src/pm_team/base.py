from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import datetime


@dataclass
class Message:
    sender: str
    content: str
    timestamp: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))


class ConversableAgentBase:
    """A minimal stub approximating an Autogen ConversableAgent.

    Responsibilities:
    - Maintain conversation history
    - Provide a respond() method to generate next message (heuristic / template based)
    - Allow injection of domain knowledge context
    """

    def __init__(self, name: str, system_prompt: str, domain_knowledge: Optional[str] = None):
        self.name = name
        self.system_prompt = system_prompt
        self.domain_knowledge = domain_knowledge or ""
        self.history: List[Message] = []

    def receive(self, message: Message):
        self.history.append(message)

    def send(self, content: str) -> Message:
        msg = Message(sender=self.name, content=content)
        self.history.append(msg)
        return msg

    def summarize_context(self, last_n: int = 6) -> str:
        tail = self.history[-last_n:]
        return "\n".join(f"[{m.sender}] {m.content}" for m in tail)

    def respond(self, prompt: str) -> Message:
        """Heuristic, context aware response.

        Looks at domain_knowledge (injected summary of artifacts) plus recent
        history to craft a concise answer. This is still rule-based so it is
        deterministic and cheap, but more helpful than simple echoing.
        """
        lower = prompt.lower()
        summary_tail = self.summarize_context(last_n=4)
        dk = self.domain_knowledge or ""

        is_status_query = any(k in lower for k in ["what is happening", "status", "summary", "progress", "update"])

        if is_status_query:
            markers: dict[str, str] = {}
            for ln in dk.splitlines():
                if ":" in ln:
                    key, val = ln.split(":", 1)
                    key = key.strip(); val = val.strip()
                    if key in {"INITIATIVE", "TASK_COUNT", "HIGH_RISK_TASKS", "BLOCKERS", "TOTAL_POINTS", "AGG_RISK", "EST_SPRINTS", "RELEASE_ITEMS"}:
                        markers[key] = val
            top_tasks: list[str] = []
            in_tasks = False
            for ln in dk.splitlines():
                if ln.startswith("TOP_TASKS:"):
                    in_tasks = True
                    continue
                if in_tasks:
                    if not ln.startswith("  - "):
                        break
                    clean = ln.strip()[3:]
                    top_tasks.append(clean.split(" (", 1)[0])
                    if len(top_tasks) >= 3:
                        break
            initiative = markers.get("INITIATIVE", "(unknown initiative)")
            blockers_val = markers.get("BLOCKERS", "None")
            blockers_phrase = "No active blockers" if blockers_val.lower() == "none" else f"Blockers: {blockers_val}"
            parts = [
                f"Status: {initiative}",
                f"Tasks: {markers.get('TASK_COUNT', '?')} ({markers.get('TOTAL_POINTS', '?')} pts)",
                f"High risk: {markers.get('HIGH_RISK_TASKS', '0')}",
                blockers_phrase,
                f"Aggregate risk score: {markers.get('AGG_RISK', '?')}"
            ]
            if 'EST_SPRINTS' in markers:
                parts.append(f"Est. sprints: {markers['EST_SPRINTS']}")
            if top_tasks:
                parts.append("Top tasks: " + ", ".join(top_tasks))
            content = ". ".join(parts) + "."
        elif "risk" in lower:
            risks: list[str] = []
            for ln in dk.splitlines():
                if ln.startswith("HIGH_RISK_TASKS:") or ln.startswith("AGG_RISK:"):
                    risks.append(ln)
            content = "Risk overview: " + ("; ".join(risks) or "No significant risks identified")
        elif "blocker" in lower or "blocked" in lower:
            blockers_list: list[str] = []
            for ln in dk.splitlines():
                if ln.startswith("BLOCKERS:"):
                    blockers_list.append(ln)
            content = blockers_list[0] if blockers_list else "No blockers recorded in the current plan."
        elif "tasks" in lower or "plan" in lower:
            tasks_section: list[str] = []
            in_tasks = False
            for ln in dk.splitlines():
                if ln.startswith("TOP_TASKS:"):
                    in_tasks = True
                    continue
                if in_tasks:
                    if not ln.startswith("  - "):
                        break
                    tasks_section.append(ln.strip())
            content = "Planned tasks (priority order): " + ", ".join(tasks_section[:6])
        else:
            content = f"Answer (heuristic): I considered recent context and artifacts. Your request: {prompt[:160]}"

        if summary_tail and not is_status_query:
            content += f"\nContext: {summary_tail[:240]}"
        return self.send(content)

    def inject_domain_update(self, update: str):
        self.domain_knowledge += f"\n[UPDATE] {update}"


def now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()

__all__ = ["ConversableAgentBase", "Message", "now_iso"]
