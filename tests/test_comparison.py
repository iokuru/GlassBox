import pytest
from glassbox.comparison.langchain_baseline import compare_agents


def test_comparison_rate_limit_scenario():
    task = "Fix recursive Fibonacci function:\n```python\ndef fib(n): return fib(n-1)+fib(n-2)\n```"
    results = compare_agents(task, inject_scenario="rate_limit")

    assert "glassbox" in results
    assert "standard_react" in results

    gb = results["glassbox"]
    lc = results["standard_react"]

    # GlassBox self-heals around the rate limit
    assert gb["succeeded"] is True
    assert gb["failures_detected"] >= 1
    assert gb["recoveries_applied"] >= 1

    # Standard ReAct fails or hides errors
    assert lc["succeeded"] is False
    assert lc["opaque_failures_hidden"] >= 1
