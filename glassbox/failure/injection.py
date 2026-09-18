from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from glassbox.types import Observation


class FaultType(str, Enum):
    RATE_LIMIT_429 = "rate_limit_429"
    TIMEOUT = "timeout"
    MALFORMED_OUTPUT = "malformed_output"
    IRRELEVANT_RESULT = "irrelevant_result"
    AUTH_ERROR = "auth_error"
    SERVER_CRASH = "server_crash"


@dataclass
class FaultRule:
    target_tool: str
    fault_type: FaultType
    trigger_on_call_count: Optional[int] = None
    trigger_probability: float = 1.0
    active: bool = True
    invocations: int = 0


class FaultInjector:
    def __init__(self) -> None:
        self.rules: List[FaultRule] = []

    def add_rule(
        self,
        target_tool: str,
        fault_type: FaultType,
        trigger_on_call_count: Optional[int] = None,
        trigger_probability: float = 1.0,
    ) -> FaultRule:
        rule = FaultRule(
            target_tool=target_tool,
            fault_type=fault_type,
            trigger_on_call_count=trigger_on_call_count,
            trigger_probability=trigger_probability,
        )
        self.rules.append(rule)
        return rule

    def clear(self) -> None:
        self.rules.clear()

    def intercept(self, tool_name: str, params: Dict[str, Any], normal_executor: Callable[[], Observation]) -> Observation:
        for rule in self.rules:
            if not rule.active or rule.target_tool != tool_name:
                continue

            rule.invocations += 1

            if rule.trigger_on_call_count is not None and rule.invocations != rule.trigger_on_call_count:
                continue

            return self._generate_fault_observation(rule, tool_name, params)

        return normal_executor()

    def _generate_fault_observation(self, rule: FaultRule, tool_name: str, params: Dict[str, Any]) -> Observation:
        fault = rule.fault_type

        if fault == FaultType.RATE_LIMIT_429:
            return Observation(
                content="HTTP 429 Client Error: Too Many Requests for url: https://api.search.internal/v1/query. Rate limit exceeded.",
                is_error=True,
                metadata={"error_type": "rate_limited", "status_code": 429, "tool_name": tool_name},
            )

        if fault == FaultType.TIMEOUT:
            return Observation(
                content=f"Execution timed out after 8.0 seconds while invoking '{tool_name}'. Subprocess hung or infinite loop detected.",
                is_error=True,
                metadata={"error_type": "execution_timeout", "timeout_seconds": 8.0, "tool_name": tool_name},
            )

        if fault == FaultType.IRRELEVANT_RESULT:
            return Observation(
                content="Warning: Search query returned 0 high-confidence results. All hits below relevance threshold 0.15.",
                is_error=True,
                metadata={"error_type": "irrelevant_result", "tool_name": tool_name},
            )

        if fault == FaultType.AUTH_ERROR:
            return Observation(
                content="HTTP 401 Unauthorized: Invalid API key or expired token for service.",
                is_error=True,
                metadata={"error_type": "auth_error", "tool_name": tool_name},
            )

        if fault == FaultType.SERVER_CRASH:
            return Observation(
                content="HTTP 500 Internal Server Error: Remote sandbox worker unexpectedly terminated.",
                is_error=True,
                metadata={"error_type": "runtime_exception", "tool_name": tool_name},
            )

        return Observation(
            content="Unknown simulated fault injected.",
            is_error=True,
            metadata={"error_type": "generic_fault", "tool_name": tool_name},
        )
