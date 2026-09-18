from __future__ import annotations

from typing import Optional
from glassbox.executor import CodeExecutor
from glassbox.types import Observation


class CodeSandboxTool:
    def __init__(self, executor: Optional[CodeExecutor] = None) -> None:
        self.executor = executor or CodeExecutor()

    def run_python_code(self, code: str) -> Observation:
        """Execute a Python snippet inside an isolated subprocess and return stdout/stderr."""
        if not code or not code.strip():
            return Observation(
                content="Error: Provided code snippet is empty.",
                is_error=True,
                metadata={"error_type": "invalid_arguments"},
            )
        return self.executor.execute(code)
