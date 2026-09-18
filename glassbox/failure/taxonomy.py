from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from glassbox.types import FailureType


class FailureSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    FATAL = "fatal"


@dataclass(frozen=True)
class FailureDescriptor:
    failure_type: FailureType
    severity: FailureSeverity
    is_recoverable: bool
    default_strategy_name: str
    description_pattern: str


TAXONOMY_CATALOG = {
    FailureType.TOOL_NOT_FOUND: FailureDescriptor(
        failure_type=FailureType.TOOL_NOT_FOUND,
        severity=FailureSeverity.MEDIUM,
        is_recoverable=True,
        default_strategy_name="switch_tool",
        description_pattern="Requested tool is not registered in the runtime registry.",
    ),
    FailureType.INVALID_ARGUMENTS: FailureDescriptor(
        failure_type=FailureType.INVALID_ARGUMENTS,
        severity=FailureSeverity.LOW,
        is_recoverable=True,
        default_strategy_name="retry_with_mutated_input",
        description_pattern="Tool arguments failed type signature or schema validation.",
    ),
    FailureType.EXECUTION_TIMEOUT: FailureDescriptor(
        failure_type=FailureType.EXECUTION_TIMEOUT,
        severity=FailureSeverity.HIGH,
        is_recoverable=True,
        default_strategy_name="patch_environment",
        description_pattern="Tool or code execution exceeded hard deadline.",
    ),
    FailureType.RUNTIME_EXCEPTION: FailureDescriptor(
        failure_type=FailureType.RUNTIME_EXCEPTION,
        severity=FailureSeverity.MEDIUM,
        is_recoverable=True,
        default_strategy_name="retry_with_mutated_input",
        description_pattern="Python interpreter raised an unhandled runtime error.",
    ),
    FailureType.SYNTAX_ERROR: FailureDescriptor(
        failure_type=FailureType.SYNTAX_ERROR,
        severity=FailureSeverity.LOW,
        is_recoverable=True,
        default_strategy_name="retry_with_mutated_input",
        description_pattern="Code failed Python AST parser validation.",
    ),
    FailureType.RATE_LIMITED: FailureDescriptor(
        failure_type=FailureType.RATE_LIMITED,
        severity=FailureSeverity.HIGH,
        is_recoverable=True,
        default_strategy_name="switch_tool",
        description_pattern="Upstream service or search endpoint returned rate limit (HTTP 429).",
    ),
    FailureType.IRRELEVANT_RESULT: FailureDescriptor(
        failure_type=FailureType.IRRELEVANT_RESULT,
        severity=FailureSeverity.LOW,
        is_recoverable=True,
        default_strategy_name="retry_with_mutated_input",
        description_pattern="Tool observation returned low-quality or off-topic information.",
    ),
    FailureType.LOOP_DETECTED: FailureDescriptor(
        failure_type=FailureType.LOOP_DETECTED,
        severity=FailureSeverity.HIGH,
        is_recoverable=True,
        default_strategy_name="break_loop",
        description_pattern="Agent is trapped in repetitive action cycle or stagnant reasoning.",
    ),
    FailureType.BUDGET_EXCEEDED: FailureDescriptor(
        failure_type=FailureType.BUDGET_EXCEEDED,
        severity=FailureSeverity.FATAL,
        is_recoverable=False,
        default_strategy_name="escalate_to_user",
        description_pattern="Agent exhausted total step budget or execution time limit.",
    ),
}
