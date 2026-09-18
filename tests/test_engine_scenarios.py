import pytest
from glassbox.config import AgentConfig
from glassbox.engine import AgentEngine
from glassbox.failure.injection import FaultType
from glassbox.types import AgentStatus


def test_engine_full_debugging_scenario(engine: AgentEngine):
    task = (
        "Debug and fix the recursive Fibonacci function:\n"
        "```python\n"
        "def fib(n):\n"
        "    return fib(n - 1) + fib(n - 2)\n"
        "print(fib(5))\n"
        "```"
    )
    trace = engine.run(task)
    assert trace.status == AgentStatus.SUCCEEDED
    assert trace.total_failures_encountered > 0
    assert trace.total_recoveries_applied > 0
    assert len(trace.steps) > 1
    assert "Resolved the bug" in (trace.final_answer or "")


def test_engine_rate_limit_fault_and_recovery():
    config = AgentConfig(max_steps=8, timeout_seconds=10.0)
    engine = AgentEngine(config=config)
    engine.fault_injector.add_rule("search_web", FaultType.RATE_LIMIT_429, trigger_on_call_count=1)

    task = "Find docs and fix recursion error:\n```python\ndef fib(n): return fib(n-1)+fib(n-2)\n```"
    trace = engine.run(task)
    assert trace.status == AgentStatus.SUCCEEDED
    assert any(s.failure and s.failure.failure_type.value == "rate_limited" for s in trace.steps)


def test_engine_budget_limit_enforcement():
    config = AgentConfig(max_steps=2, timeout_seconds=10.0)
    engine = AgentEngine(config=config)

    task = "Debug complex code requiring multiple steps:\n```python\ndef f(x): return f(x)\n```"
    trace = engine.run(task)
    assert trace.status == AgentStatus.BUDGET_EXHAUSTED
    assert len(trace.steps) == 2
