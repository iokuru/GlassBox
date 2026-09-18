from __future__ import annotations

import re
from typing import Dict, List, Optional
from glassbox.types import Action, FailureRecord, FailureType, Observation


class FailureClassifier:
    def __init__(self) -> None:
        self.exception_patterns = [
            (r"SyntaxError|IndentationError", FailureType.SYNTAX_ERROR),
            (r"429|Too Many Requests|rate.?limit", FailureType.RATE_LIMITED),
            (r"timed? ?out|TimeoutExpired", FailureType.EXECUTION_TIMEOUT),
            (r"Tool '[^']+' not found", FailureType.TOOL_NOT_FOUND),
            (r"missing \d+ required positional argument|unexpected keyword argument|Argument error", FailureType.INVALID_ARGUMENTS),
            (r"too broad or ambiguous|irrelevant|0 high-confidence", FailureType.IRRELEVANT_RESULT),
            (r"(RecursionError|IndexError|KeyError|TypeError|ZeroDivisionError|ValueError|AttributeError|NameError|ImportError): (.*)", FailureType.RUNTIME_EXCEPTION),
        ]

    def classify(self, observation: Observation, action: Optional[Action] = None) -> Optional[FailureRecord]:
        if not observation.is_error:
            return None

        content = observation.content or ""
        meta_err = observation.metadata.get("error_type")

        if meta_err == "syntax_error":
            return FailureRecord(
                failure_type=FailureType.SYNTAX_ERROR,
                description=content.splitlines()[0] if content else "Syntax error in code",
                error_signature="SyntaxError",
                raw_error=content,
            )

        if meta_err == "execution_timeout":
            return FailureRecord(
                failure_type=FailureType.EXECUTION_TIMEOUT,
                description="Process execution exceeded timeout threshold",
                error_signature="TimeoutExpired",
                raw_error=content,
            )

        if meta_err == "tool_not_found":
            tool_name = observation.metadata.get("tool_name", "unknown")
            return FailureRecord(
                failure_type=FailureType.TOOL_NOT_FOUND,
                description=f"Attempted to invoke unregistered tool '{tool_name}'",
                error_signature=f"UnregisteredTool:{tool_name}",
                raw_error=content,
            )

        if meta_err == "invalid_arguments":
            return FailureRecord(
                failure_type=FailureType.INVALID_ARGUMENTS,
                description="Tool argument validation failed",
                error_signature="InvalidArgumentError",
                raw_error=content,
            )

        if meta_err == "irrelevant_result":
            return FailureRecord(
                failure_type=FailureType.IRRELEVANT_RESULT,
                description="Search query returned non-informative or noisy results",
                error_signature="VagueQueryError",
                raw_error=content,
            )

        for pattern, failure_type in self.exception_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                sig = match.group(0).splitlines()[0]
                return FailureRecord(
                    failure_type=failure_type,
                    description=f"Detected {failure_type.value}: {sig[:80]}",
                    error_signature=sig,
                    raw_error=content,
                )

        return FailureRecord(
            failure_type=FailureType.RUNTIME_EXCEPTION,
            description=content.splitlines()[0][:100] if content else "Generic tool failure",
            error_signature="GenericRuntimeError",
            raw_error=content,
        )
