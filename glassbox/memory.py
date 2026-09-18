from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from glassbox.types import Action, ExecutionTrace, FailureRecord, Observation, RecoveryRecord, StepRecord


class AgentMemory:
    def __init__(self, max_working_steps: int = 10) -> None:
        self.max_working_steps = max_working_steps
        self.steps: List[StepRecord] = []
        self.failure_history: List[FailureRecord] = []
        self.discarded_hypotheses: List[str] = []
        self.current_working_solution: Optional[str] = None

    def add_step(self, step: StepRecord) -> None:
        self.steps.append(step)
        if step.failure:
            self.failure_history.append(step.failure)

    def record_hypothesis_failure(self, hypothesis: str, reason: str) -> None:
        self.discarded_hypotheses.append(f"{hypothesis} (Failed: {reason})")

    def update_working_solution(self, solution: str) -> None:
        self.current_working_solution = solution

    def get_working_context(self) -> List[StepRecord]:
        return self.steps[-self.max_working_steps:]

    def get_total_failures(self) -> int:
        return len(self.failure_history)

    def format_history_for_prompt(self) -> str:
        if not self.steps:
            return "No previous steps executed yet."

        blocks: List[str] = []
        for s in self.get_working_context():
            block = [f"--- Step {s.step_number} ---"]
            block.append(f"Thought: {s.thought.content}")
            if s.action:
                block.append(f"Action: {s.action.tool} with params {s.action.params}")
            if s.observation:
                obs_preview = s.observation.content[:500]
                if len(s.observation.content) > 500:
                    obs_preview += "... [truncated]"
                block.append(f"Observation: {obs_preview}")
            if s.failure:
                block.append(f"[FAILURE RECORDED] Class: {s.failure.failure_type.value}, Diagnostic: {s.failure.description}")
            if s.recovery:
                block.append(f"[RECOVERY STRATEGY] Applied: {s.recovery.strategy.value}, Directive: {s.recovery.reason}")
            blocks.append("\n".join(block))

        if self.discarded_hypotheses:
            blocks.append(
                "Known Discarded Hypotheses (DO NOT REPEAT):\n- " + "\n- ".join(self.discarded_hypotheses[-4:])
            )

        return "\n\n".join(blocks)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_steps": len(self.steps),
            "total_failures": len(self.failure_history),
            "discarded_hypotheses": self.discarded_hypotheses,
            "current_working_solution": self.current_working_solution,
            "steps": [s.model_dump() for s in self.steps],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)
