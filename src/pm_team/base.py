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
        # Very naive heuristic response
        content = f"(Heuristic response) {self.name} acknowledges: {prompt[:200]}"
        return self.send(content)

    def inject_domain_update(self, update: str):
        self.domain_knowledge += f"\n[UPDATE] {update}"


def now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()

__all__ = ["ConversableAgentBase", "Message", "now_iso"]
