import pytest
from glassbox.executor import CodeExecutor


def test_executor_syntax_error(executor: CodeExecutor):
    broken_code = "def broken(:\n    pass"
    obs = executor.execute(broken_code)
    assert obs.is_error
    assert obs.metadata.get("error_type") == "syntax_error"
    assert "SyntaxError" in obs.content


def test_executor_successful_run(executor: CodeExecutor):
    code = "print('GlassBox Execution Verified')"
    obs = executor.execute(code)
    assert not obs.is_error
    assert obs.content == "GlassBox Execution Verified"


def test_executor_runtime_exception(executor: CodeExecutor):
    code = "numbers = [1, 2]\nprint(numbers[10])"
    obs = executor.execute(code)
    assert obs.is_error
    assert obs.metadata.get("error_type") == "runtime_exception"
    assert "IndexError" in obs.content


def test_executor_timeout_guard(executor: CodeExecutor):
    infinite_loop = "while True:\n    pass"
    obs = executor.execute(infinite_loop, timeout=0.8)
    assert obs.is_error
    assert obs.metadata.get("error_type") == "execution_timeout"
    assert "timed out" in obs.content.lower()
