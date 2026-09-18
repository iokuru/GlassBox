from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BUDGET_EXHAUSTED = "budget_exhausted"
    ESCALATED = "escalated"


class FailureType(str, Enum):
    NONE = "none"
    TOOL_NOT_FOUND = "tool_not_found"
    INVALID_ARGUMENTS = "invalid_arguments"
    EXECUTION_TIMEOUT = "execution_timeout"
    RUNTIME_EXCEPTION = "runtime_exception"
    SYNTAX_ERROR = "syntax_error"
    RATE_LIMITED = "rate_limited"
    IRRELEVANT_RESULT = "irrelevant_result"
    LOOP_DETECTED = "loop_detected"
    BUDGET_EXCEEDED = "budget_exceeded"


class RecoveryAction(str, Enum):
    RETRY_WITH_MUTATED_INPUT = "retry_with_mutated_input"
    SWITCH_TOOL = "switch_tool"
    PATCH_ENVIRONMENT = "patch_environment"
    BREAK_LOOP = "break_loop"
    ESCALATE_TO_USER = "escalate_to_user"
    ABORT = "abort"


class Thought(BaseModel):
    content: str
    timestamp: float = Field(default_factory=time.time)


class Action(BaseModel):
    tool: str
    params: Dict[str, Any] = Field(default_factory=dict)
    rationale: Optional[str] = None

    def signature(self) -> str:
        param_keys = sorted(self.params.keys())
        param_repr = ",".join(f"{k}:{str(self.params[k])[:30]}" for k in param_keys)
        return f"{self.tool}({param_repr})"


class Observation(BaseModel):
    content: str
    is_error: bool = False
    raw_output: Any = None
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FailureRecord(BaseModel):
    failure_type: FailureType
    description: str
    error_signature: Optional[str] = None
    attempt_count: int = 1
    raw_error: Optional[str] = None


class RecoveryRecord(BaseModel):
    strategy: RecoveryAction
    reason: str
    modifications: Dict[str, Any] = Field(default_factory=dict)
    applied: bool = True


class StepRecord(BaseModel):
    step_number: int
    thought: Thought
    action: Optional[Action] = None
    observation: Optional[Observation] = None
    failure: Optional[FailureRecord] = None
    recovery: Optional[RecoveryRecord] = None
    duration_ms: float = 0.0
    timestamp: float = Field(default_factory=time.time)


class ExecutionTrace(BaseModel):
    session_id: str
    task: str
    status: AgentStatus = AgentStatus.RUNNING
    steps: List[StepRecord] = Field(default_factory=list)
    final_answer: Optional[str] = None
    total_duration_ms: float = 0.0
    total_failures_encountered: int = 0
    total_recoveries_applied: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
