from __future__ import annotations

from typing import Any, Dict, List, Optional
from glassbox.failure.taxonomy import TAXONOMY_CATALOG
from glassbox.types import Action, FailureRecord, FailureType, RecoveryAction, RecoveryRecord


class RecoveryEngine:
    def __init__(self, max_retries: int = 3) -> None:
        self.max_retries = max_retries

    def plan_recovery(
        self,
        failure: FailureRecord,
        last_action: Optional[Action],
        available_tools: List[str],
        failure_history: List[FailureRecord],
    ) -> RecoveryRecord:
        failure_type = failure.failure_type
        descriptor = TAXONOMY_CATALOG.get(failure_type)

        same_failure_count = sum(1 for f in failure_history if f.failure_type == failure_type)

        if same_failure_count >= self.max_retries:
            return RecoveryRecord(
                strategy=RecoveryAction.ESCALATE_TO_USER,
                reason=f"Exceeded maximum retries ({self.max_retries}) for failure '{failure_type.value}'. Escalating.",
                modifications={"status": "escalation_required"},
            )

        if failure_type == FailureType.RATE_LIMITED:
            alternative_tools = [t for t in available_tools if last_action and t != last_action.tool]
            fallback_tool = "lookup_documentation" if "lookup_documentation" in alternative_tools else (
                alternative_tools[0] if alternative_tools else None
            )
            return RecoveryRecord(
                strategy=RecoveryAction.SWITCH_TOOL,
                reason="Upstream rate limit hit (HTTP 429). Switching to alternate knowledge tool.",
                modifications={"suggested_tool": fallback_tool},
            )

        if failure_type == FailureType.LOOP_DETECTED:
            forbidden_tool = last_action.tool if last_action else ""
            remaining_tools = [t for t in available_tools if t != forbidden_tool]
            return RecoveryRecord(
                strategy=RecoveryAction.BREAK_LOOP,
                reason="Agent caught in repetitive cycle. Forbidding repeated invocation and forcing state transition.",
                modifications={"forbidden_tool": forbidden_tool, "candidate_tools": remaining_tools},
            )

        if failure_type == FailureType.SYNTAX_ERROR:
            return RecoveryRecord(
                strategy=RecoveryAction.RETRY_WITH_MUTATED_INPUT,
                reason="Python syntax error caught by AST parser. Reconstructing code with valid Python syntax.",
                modifications={"focus": "syntax_correction"},
            )

        if failure_type == FailureType.EXECUTION_TIMEOUT:
            return RecoveryRecord(
                strategy=RecoveryAction.PATCH_ENVIRONMENT,
                reason="Subprocess execution timed out. Potential infinite loop or missing termination check.",
                modifications={"action": "add_termination_guard_or_iteration_counter"},
            )

        if failure_type == FailureType.IRRELEVANT_RESULT:
            return RecoveryRecord(
                strategy=RecoveryAction.RETRY_WITH_MUTATED_INPUT,
                reason="Query was too ambiguous or returned zero matches. Re-anchoring keywords to concrete error signature.",
                modifications={"query_strategy": "add_error_name_and_library_context"},
            )

        if failure_type == FailureType.INVALID_ARGUMENTS:
            return RecoveryRecord(
                strategy=RecoveryAction.RETRY_WITH_MUTATED_INPUT,
                reason="Tool signature arguments did not match schema. Realigning argument keys.",
                modifications={"action": "rebind_arguments_to_schema"},
            )

        if failure_type == FailureType.TOOL_NOT_FOUND:
            closest_tool = available_tools[0] if available_tools else "run_python_code"
            return RecoveryRecord(
                strategy=RecoveryAction.SWITCH_TOOL,
                reason=f"Hallucinated tool. Redirecting to existing registered tool '{closest_tool}'.",
                modifications={"suggested_tool": closest_tool},
            )

        return RecoveryRecord(
            strategy=RecoveryAction.RETRY_WITH_MUTATED_INPUT,
            reason="Runtime exception encountered. Inspecting traceback to refine hypothesis and fix code.",
            modifications={"action": "analyze_traceback_and_mutate"},
        )

    def generate_recovery_prompt(self, failure: FailureRecord, recovery: RecoveryRecord) -> str:
        return (
            f"[SYSTEM COGNITION MONITOR - FAILURE DETECTED]\n"
            f"Failure Class: {failure.failure_type.value.upper()}\n"
            f"Diagnostic: {failure.description}\n"
            f"Prescribed Recovery Strategy: {recovery.strategy.value.upper()}\n"
            f"Recovery Directive: {recovery.reason}\n"
            f"Required Adaptation: Do NOT repeat the previous failing action. Apply the prescribed strategy above."
        )
