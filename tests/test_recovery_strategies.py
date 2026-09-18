import pytest
from glassbox.failure.recovery import RecoveryEngine
from glassbox.types import Action, FailureRecord, FailureType, RecoveryAction


def test_rate_limit_recovery_switches_tool():
    engine = RecoveryEngine()
    failure = FailureRecord(
        failure_type=FailureType.RATE_LIMITED,
        description="Search endpoint returned 429",
    )
    last_action = Action(tool="search_web", params={"query": "python"})
    available_tools = ["search_web", "lookup_documentation", "run_python_code"]

    plan = engine.plan_recovery(failure, last_action, available_tools, [])
    assert plan.strategy == RecoveryAction.SWITCH_TOOL
    assert plan.modifications.get("suggested_tool") == "lookup_documentation"


def test_loop_recovery_breaks_cycle():
    engine = RecoveryEngine()
    failure = FailureRecord(
        failure_type=FailureType.LOOP_DETECTED,
        description="Stagnant loop detected",
    )
    last_action = Action(tool="search_web", params={"query": "python"})
    available_tools = ["search_web", "run_python_code"]

    plan = engine.plan_recovery(failure, last_action, available_tools, [])
    assert plan.strategy == RecoveryAction.BREAK_LOOP
    assert plan.modifications.get("forbidden_tool") == "search_web"


def test_max_retries_escalates_to_user():
    engine = RecoveryEngine(max_retries=2)
    failure = FailureRecord(
        failure_type=FailureType.SYNTAX_ERROR,
        description="Syntax error repeatedly failed",
    )
    history = [
        failure,
        failure,
    ]

    plan = engine.plan_recovery(failure, None, ["run_python_code"], history)
    assert plan.strategy == RecoveryAction.ESCALATE_TO_USER
