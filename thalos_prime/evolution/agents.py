"""Agent genomes, specialization, bidding, and dynamic spawning."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
import uuid


@dataclass
class Genome:
    identity: str
    generation: int = 0
    reasoning_strategy: tuple[str, ...] = ("analysis", "verification")
    tools: tuple[str, ...] = ()
    workflow: tuple[str, ...] = ("analyze", "plan", "execute", "review")
    mutation_policy: tuple[str, ...] = (
        "prompt_strategy", "tool_selection", "workflow_order", "memory_filtering"
    )
    metrics: dict[str, float] = field(default_factory=lambda: {
        "success_rate": 0.5, "speed_score": 0.5, "efficiency_score": 0.5,
    })


class BaseAgent:
    def __init__(self, role: str, genome: Genome | None = None, runner: Callable[..., Any] | None = None) -> None:
        self.agent_id = str(uuid.uuid4())
        self.role = role
        self.genome = genome or Genome(identity=self.agent_id)
        self.runner = runner
        self.tasks_completed = 0
        self.tasks_failed = 0

    def score_task(self, task: dict[str, Any]) -> float:
        required = set(task.get("capabilities", ()))
        available = set(self.genome.tools) | set(self.genome.reasoning_strategy)
        fit = len(required & available) / max(len(required), 1)
        reliability = self.genome.metrics.get("success_rate", 0.5)
        return 0.7 * fit + 0.3 * reliability

    def act(self, task: dict[str, Any], context: dict[str, Any] | None = None) -> Any:
        if self.runner is None:
            return {"agent_id": self.agent_id, "role": self.role, "task": task, "status": "planned"}
        return self.runner(task, context or {})

    def record(self, success: bool) -> None:
        if success:
            self.tasks_completed += 1
        else:
            self.tasks_failed += 1
        total = self.tasks_completed + self.tasks_failed
        self.genome.metrics["success_rate"] = self.tasks_completed / total if total else 0.5


class AgentPool:
    def __init__(self, agents: list[BaseAgent] | None = None) -> None:
        self.agents = list(agents or [])

    def bid(self, task: dict[str, Any]) -> BaseAgent:
        if not self.agents:
            raise RuntimeError("no agents available")
        return max(self.agents, key=lambda agent: (agent.score_task(task), agent.agent_id))

    def spawn(self, purpose: str, tools: tuple[str, ...] = (), strategy: tuple[str, ...] = ()) -> BaseAgent:
        genome = Genome(
            identity=str(uuid.uuid4()), generation=max((a.genome.generation for a in self.agents), default=0) + 1,
            tools=tools, reasoning_strategy=strategy or ("analysis",),
        )
        agent = BaseAgent(purpose, genome=genome)
        self.agents.append(agent)
        return agent


class AgentFactory:
    def create(self, purpose: str, tools: tuple[str, ...] = (), strategy: tuple[str, ...] = ()) -> BaseAgent:
        return BaseAgent(
            purpose,
            Genome(identity=str(uuid.uuid4()), tools=tools, reasoning_strategy=strategy or ("analysis",)),
        )
