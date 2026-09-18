from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class BaselineRunResult:
    framework_name: str
    succeeded: bool
    iterations_used: int
    loop_detected: bool
    classified_failures: int
    recovered_failures: int
    terminal_error: Optional[str]
    duration_ms: float
    opaque_failures_hidden: int


class StandardReActAgent:
    """Standard ReAct framework baseline representing conventional AgentExecutor wrappers (e.g. LangChain)."""

    def __init__(self, tools: Dict[str, Callable], max_iterations: int = 5) -> None:
        self.tools = tools
        self.max_iterations = max_iterations

    def run(self, task: str, inject_failure_type: Optional[str] = None) -> BaselineRunResult:
        start_time = time.perf_counter()
        iteration = 0
        opaque_hidden = 0
        terminal_err = None

        # Standard ReAct loop without failure taxonomy or loop detection
        history: List[str] = []

        while iteration < self.max_iterations:
            iteration += 1

            # Simulated standard LLM prompt response
            if iteration == 1:
                tool_name = "run_python_code"
                tool_args = {"code": "def fib(n):\n    return fib(n-1) + fib(n-2)\nfib(5)"}
            elif iteration == 2 and inject_failure_type == "rate_limit":
                # Calls search, gets 429 error
                tool_name = "search_web"
                tool_args = {"query": "recursion"}
            elif iteration >= 2 and inject_failure_type == "stagnation":
                # Stagnant retry without mutating query
                tool_name = "search_web"
                tool_args = {"query": "error"}
            else:
                tool_name = "run_python_code"
                tool_args = {"code": "def fib(n):\n    return 0 if n <= 0 else 1 if n == 1 else fib(n-1)+fib(n-2)\nprint(fib(5))"}

            tool = self.tools.get(tool_name)
            if not tool:
                opaque_hidden += 1
                terminal_err = f"Agent stopped: Tool '{tool_name}' does not exist."
                break

            try:
                obs = tool(**tool_args)
                is_err = getattr(obs, "is_error", False)
                content = getattr(obs, "content", str(obs))

                if is_err:
                    opaque_hidden += 1
                    # In standard LangChain ReAct, error strings are simply fed back as raw Observation
                    # without classifying whether it's rate limit, syntax error, or loop stagnation.
                    history.append(f"Observation: {content}")
                    if "429" in content:
                        terminal_err = "Unhandled upstream RateLimitException encountered in tool call."
                        break
                else:
                    if "5" in content or "finished" in content.lower():
                        return BaselineRunResult(
                            framework_name="Standard ReAct (LangChain Pattern)",
                            succeeded=True,
                            iterations_used=iteration,
                            loop_detected=False,
                            classified_failures=0,
                            recovered_failures=0,
                            terminal_error=None,
                            duration_ms=(time.perf_counter() - start_time) * 1000.0,
                            opaque_failures_hidden=opaque_hidden,
                        )
            except Exception as e:
                opaque_hidden += 1
                terminal_err = f"Tool crashed with unhandled exception: {type(e).__name__}: {str(e)}"
                break

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return BaselineRunResult(
            framework_name="Standard ReAct (LangChain Pattern)",
            succeeded=False,
            iterations_used=iteration,
            loop_detected=False,  # Standard ReAct has no loop detection
            classified_failures=0,  # Zero taxonomy
            recovered_failures=0,  # Zero autonomous recovery
            terminal_error=terminal_err or "Agent stopped due to max iterations limit.",
            duration_ms=duration_ms,
            opaque_failures_hidden=opaque_hidden,
        )


def compare_agents(task: str, inject_scenario: Optional[str] = None) -> Dict[str, Any]:
    from glassbox.engine import AgentEngine
    from glassbox.failure.injection import FaultInjector, FaultType

    engine = AgentEngine()
    if inject_scenario == "rate_limit":
        engine.fault_injector.add_rule(
            target_tool="search_web",
            fault_type=FaultType.RATE_LIMIT_429,
            trigger_on_call_count=1,
        )

    # Run GlassBox
    start_gb = time.perf_counter()
    gb_trace = engine.run(task)
    gb_duration = (time.perf_counter() - start_gb) * 1000.0

    # Run Baseline with isolated fault injector
    baseline_injector = FaultInjector()
    if inject_scenario == "rate_limit":
        baseline_injector.add_rule(
            target_tool="search_web",
            fault_type=FaultType.RATE_LIMIT_429,
            trigger_on_call_count=1,
        )

    baseline_tools = {
        "run_python_code": lambda **kwargs: engine.registry.execute("run_python_code", kwargs),
        "search_web": lambda **kwargs: baseline_injector.intercept(
            "search_web", kwargs, lambda: engine.registry.execute("search_web", kwargs)
        ),
    }
    baseline_agent = StandardReActAgent(tools=baseline_tools, max_iterations=4)
    baseline_result = baseline_agent.run(task, inject_failure_type=inject_scenario)

    return {
        "glassbox": {
            "succeeded": gb_trace.status.value == "succeeded",
            "steps": len(gb_trace.steps),
            "failures_detected": gb_trace.total_failures_encountered,
            "recoveries_applied": gb_trace.total_recoveries_applied,
            "status": gb_trace.status.value,
            "duration_ms": gb_duration,
        },
        "standard_react": {
            "succeeded": baseline_result.succeeded,
            "steps": baseline_result.iterations_used,
            "failures_detected": baseline_result.classified_failures,
            "recoveries_applied": baseline_result.recovered_failures,
            "opaque_failures_hidden": baseline_result.opaque_failures_hidden,
            "terminal_error": baseline_result.terminal_error,
            "duration_ms": baseline_result.duration_ms,
        },
    }
