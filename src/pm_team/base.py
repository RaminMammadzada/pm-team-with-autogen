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

        def _section(name: str, text: str) -> str:
            return f"{name}: {text}" if text else ""

        # Simple intent detection
        if any(k in lower for k in ["what is happening", "status", "summary", "progress", "update"]):
            # Extract pre-computed summary lines from domain knowledge tokens
            lines = []
            for marker in ["INITIATIVE:", "TASK_COUNT:", "HIGH_RISK_TASKS:", "BLOCKERS:", "TOTAL_POINTS:", "AGG_RISK:"]:
                for ln in dk.splitlines():
                    if ln.startswith(marker):
                        lines.append(ln)
                        break
            content = "Project status -> " + "; ".join(lines)
        elif "risk" in lower:
            risks = []
            for ln in dk.splitlines():
                if ln.startswith("HIGH_RISK_TASKS:") or ln.startswith("AGG_RISK:"):
                    risks.append(ln)
            content = "Risk overview: " + ("; ".join(risks) or "No significant risks identified")
        elif "blocker" in lower or "blocked" in lower:
            bl = []
            for ln in dk.splitlines():
                if ln.startswith("BLOCKERS:"):
                    bl.append(ln)
            content = bl[0] if bl else "No blockers recorded in the current plan."
        elif "tasks" in lower or "plan" in lower:
            # Provide top tasks with priority
            tasks_section = []
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

        # Add brief provenance tail
        if summary_tail:
            content += f"\nContext: {summary_tail[:240]}"
        return self.send(content)

    def inject_domain_update(self, update: str):
        self.domain_knowledge += f"\n[UPDATE] {update}"


def now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()

__all__ = ["ConversableAgentBase", "Message", "now_iso"]
