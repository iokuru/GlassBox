import pytest
from glassbox.failure.injection import FaultInjector, FaultType
from glassbox.types import Observation


def test_fault_injector_rule_matching():
    injector = FaultInjector()
    injector.add_rule("search_web", FaultType.RATE_LIMIT_429, trigger_on_call_count=1)

    # First call triggers fault
    obs1 = injector.intercept("search_web", {}, lambda: Observation(content="normal output"))
    assert obs1.is_error
    assert obs1.metadata.get("error_type") == "rate_limited"
    assert "429" in obs1.content

    # Second call passes through normally
    obs2 = injector.intercept("search_web", {}, lambda: Observation(content="normal output"))
    assert not obs2.is_error
    assert obs2.content == "normal output"


def test_fault_injector_target_tool_isolation():
    injector = FaultInjector()
    injector.add_rule("search_web", FaultType.TIMEOUT)

    # Unaffected tool
    obs = injector.intercept("run_python_code", {}, lambda: Observation(content="executed"))
    assert not obs.is_error
    assert obs.content == "executed"
