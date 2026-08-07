"""Multi-agent message board, task delegation, verification, and council."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
import hashlib
import json
import uuid

from .agents import AgentPool
from .memory import CognitiveMemory


@dataclass(frozen=True)
class Message:
    message_id: str
    sender: str
    type: str
    content: Any
    related_task: str | None = None
    visibility: str = "public"
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    signature: str = ""


class MessageBoard:
    def __init__(self) -> None:
        self.messages: list[Message] = []

    def publish(self, sender: str, type: str, content: Any, related_task: str | None = None) -> Message:
        message_id = str(uuid.uuid4())
        canonical = json.dumps({"id": message_id, "sender": sender, "type": type, "content": content}, sort_keys=True, default=str)
        signature = hashlib.sha256(canonical.encode()).hexdigest()
        message = Message(message_id, sender, type, content, related_task, signature=signature)
        self.messages.append(message)
        return message

    def for_task(self, task_id: str) -> list[Message]:
        return [m for m in self.messages if m.related_task == task_id]


class TaskCoordinator:
    """Assigns work by capability bidding and keeps task lineage explicit."""

    def __init__(self, pool: AgentPool, memory: CognitiveMemory | None = None, board: MessageBoard | None = None) -> None:
        self.pool = pool
        self.memory = memory or CognitiveMemory()
        self.board = board or MessageBoard()
        self.tasks: dict[str, dict[str, Any]] = {}

    def create_task(self, title: str, description: str = "", capabilities: tuple[str, ...] = (), dependencies: tuple[str, ...] = ()) -> dict[str, Any]:
        task = {
            "task_id": str(uuid.uuid4()), "title": title, "description": description,
            "status": "pending", "capabilities": capabilities, "dependencies": dependencies,
            "assigned_to": [], "subtasks": [], "logs": [],
        }
        self.tasks[task["task_id"]] = task
        return task

    def assign(self, task_id: str) -> str:
        task = self.tasks[task_id]
        agent = self.pool.bid(task)
        task["assigned_to"] = [agent.agent_id]
        task["status"] = "active"
        self.board.publish(agent.agent_id, "request", {"action": "claim", "task": task_id}, task_id)
        return agent.agent_id

    def complete(self, task_id: str, result: Any, success: bool = True) -> None:
        task = self.tasks[task_id]
        task["status"] = "completed" if success else "failed"
        task["result"] = {"output": result, "validated": False}
        self.memory.publish("result", result, task["assigned_to"][0], confidence=0.8 if success else 0.2, tags=(task_id,))


class EvolutionCouncil:
    """Builder/Critic/Auditor scoring facade for major mutation proposals."""

    def decide(self, proposal: dict[str, Any], scores: dict[str, float]) -> tuple[bool, dict[str, Any]]:
        values = [scores.get(role, 0.0) for role in ("builder", "critic", "auditor")]
        mean = sum(values) / len(values)
        approved = mean >= 0.67 and min(values) >= 0.5
        return approved, {"scores": scores, "mean": mean, "approved": approved, "proposal": proposal}
