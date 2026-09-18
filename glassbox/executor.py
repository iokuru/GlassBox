from __future__ import annotations

import ast
import os
import subprocess
import sys
import tempfile
import time
from typing import Dict, Optional, Tuple

from glassbox.types import Observation


class CodeExecutor:
    def __init__(self, default_timeout: float = 6.0, max_output_chars: int = 4000) -> None:
        self.default_timeout = default_timeout
        self.max_output_chars = max_output_chars

    def check_syntax(self, code: str) -> Optional[Tuple[str, int]]:
        try:
            ast.parse(code)
            return None
        except SyntaxError as e:
            return (f"SyntaxError: {e.msg} at line {e.lineno}", e.lineno or 1)

    def execute(self, code: str, timeout: Optional[float] = None) -> Observation:
        exec_timeout = timeout or self.default_timeout
        start_time = time.perf_counter()

        syntax_issue = self.check_syntax(code)
        if syntax_issue:
            err_msg, line_no = syntax_issue
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return Observation(
                content=err_msg,
                is_error=True,
                execution_time_ms=duration_ms,
                metadata={
                    "error_type": "syntax_error",
                    "line": line_no,
                    "exit_code": 1,
                },
            )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
            tmp_path = tmp.name
            tmp.write(code)

        try:
            proc = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=exec_timeout,
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            stdout = proc.stdout[: self.max_output_chars]
            stderr = proc.stderr[: self.max_output_chars]

            if proc.returncode != 0:
                err_output = stderr.strip() if stderr.strip() else stdout.strip()
                return Observation(
                    content=f"Execution failed with exit code {proc.returncode}:\n{err_output}",
                    is_error=True,
                    execution_time_ms=duration_ms,
                    metadata={
                        "error_type": "runtime_exception",
                        "exit_code": proc.returncode,
                        "stdout": stdout,
                        "stderr": stderr,
                    },
                )

            output = stdout if stdout else "(Execution completed with no standard output)"
            return Observation(
                content=output.strip(),
                is_error=False,
                execution_time_ms=duration_ms,
                metadata={"exit_code": 0, "stdout": stdout},
            )

        except subprocess.TimeoutExpired:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return Observation(
                content=f"Execution timed out after {exec_timeout:.1f} seconds. Possible infinite loop or blocking call.",
                is_error=True,
                execution_time_ms=duration_ms,
                metadata={
                    "error_type": "execution_timeout",
                    "timeout_seconds": exec_timeout,
                },
            )
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
