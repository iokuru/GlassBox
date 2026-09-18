from __future__ import annotations

import sys
import time
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from glassbox.config import AgentConfig
from glassbox.engine import AgentEngine
from glassbox.failure.injection import FaultType
from glassbox.types import (
    Action,
    ExecutionTrace,
    FailureRecord,
    Observation,
    RecoveryRecord,
    StepRecord,
    Thought,
)


class TerminalCognitionRenderer:
    def __init__(self, console: Optional[Console] = None) -> None:
        self.console = console or Console()

    def render_header(self, task: str) -> None:
        title = Text("🔮 GLASS BOX — LIVE COGNITION TRACE", style="bold white on blue")
        subtitle = Text("Autonomous Debugging Agent with Explicit Failure Taxonomy & Self-Healing", style="italic cyan")
        self.console.print()
        self.console.print(Panel(subtitle, title=title, border_style="blue", padding=(1, 2)))
        self.console.print(f"[bold yellow]Task:[/bold yellow] {task}\n")

    def render_step_start(self, step_number: int) -> None:
        self.console.rule(f"[bold cyan]Cognitive Step {step_number}[/bold cyan]")

    def render_thought(self, thought: Thought) -> None:
        self.console.print(
            Panel(
                thought.content,
                title="[bold cyan]🧠 Internal Reasoning (Thought)[/bold cyan]",
                border_style="cyan",
                padding=(0, 1),
            )
        )

    def render_action(self, action: Action) -> None:
        param_summary = ", ".join(f"{k}='{str(v)[:60]}'" for k, v in action.params.items())
        content = f"[bold white]Tool:[/bold white] [green]{action.tool}[/green]\n[bold white]Arguments:[/bold white] {param_summary}"
        if action.rationale:
            content += f"\n[bold white]Rationale:[/bold white] [italic]{action.rationale}[/italic]"
        self.console.print(
            Panel(
                content,
                title="[bold yellow]⚡ Proposed Action (Router)[/bold yellow]",
                border_style="yellow",
                padding=(0, 1),
            )
        )

    def render_observation(self, obs: Observation) -> None:
        style = "red" if obs.is_error else "bright_blue"
        tag = "[bold red]FAILED[/bold red]" if obs.is_error else "[bold green]OK[/bold green]"
        title = f"[bold {style}]🔍 Observation [{tag}][/bold {style}]"
        self.console.print(
            Panel(
                obs.content,
                title=title,
                border_style=style,
                padding=(0, 1),
            )
        )

    def render_failure(self, failure: FailureRecord) -> None:
        content = (
            f"[bold red]TAXONOMY CLASS:[/bold red] {failure.failure_type.value.upper()}\n"
            f"[bold white]DIAGNOSTIC:[/bold white] {failure.description}\n"
            f"[bold white]SIGNATURE:[/bold white] {failure.error_signature or 'N/A'}"
        )
        self.console.print(
            Panel(
                content,
                title="[bold white on red] 💥 MIND BREAK: FAILURE DETECTED [/bold white on red]",
                border_style="red",
                padding=(1, 2),
            )
        )

    def render_recovery(self, recovery: RecoveryRecord) -> None:
        content = (
            f"[bold green]STRATEGY:[/bold green] {recovery.strategy.value.upper()}\n"
            f"[bold white]RATIONALE:[/bold white] {recovery.reason}\n"
            f"[bold white]MODIFICATIONS:[/bold white] {recovery.modifications}"
        )
        self.console.print(
            Panel(
                content,
                title="[bold black on green] 🛡️ SELF-HEAL: ADAPTIVE RECOVERY APPLIED [/bold black on green]",
                border_style="green",
                padding=(1, 2),
            )
        )

    def render_summary(self, trace: ExecutionTrace) -> None:
        self.console.print()
        self.console.rule("[bold magenta]Session Telemetry & Post-Mortem[/bold magenta]")

        table = Table(show_header=True, header_style="bold magenta", border_style="dim")
        table.add_column("Metric", style="white")
        table.add_column("Value", style="cyan")

        table.add_row("Execution Status", f"[bold green]{trace.status.value.upper()}[/bold green]" if trace.status.value == "succeeded" else f"[bold red]{trace.status.value.upper()}[/bold red]")
        table.add_row("Total Cognitive Steps", str(len(trace.steps)))
        table.add_row("Failures Detected & Classified", str(trace.total_failures_encountered))
        table.add_row("Self-Healing Recoveries Applied", str(trace.total_recoveries_applied))
        table.add_row("Total Runtime Duration", f"{trace.total_duration_ms:.1f} ms")

        self.console.print(table)

        if trace.final_answer:
            self.console.print(
                Panel(
                    trace.final_answer,
                    title="[bold green]🏁 Final Resolution[/bold green]",
                    border_style="green",
                    padding=(1, 2),
                )
            )
        self.console.print()


def run_cli_session(task: str, inject_fault: Optional[str] = None) -> ExecutionTrace:
    console = Console()
    renderer = TerminalCognitionRenderer(console)
    config = AgentConfig.from_env()
    engine = AgentEngine(config=config)

    # Attach live streaming UI hooks
    engine.on_step_start = renderer.render_step_start
    engine.on_thought = renderer.render_thought
    engine.on_action = renderer.render_action
    engine.on_observation = renderer.render_observation
    engine.on_failure = renderer.render_failure
    engine.on_recovery = renderer.render_recovery

    if inject_fault == "rate_limit":
        engine.fault_injector.add_rule("search_web", FaultType.RATE_LIMIT_429, trigger_on_call_count=1)
    elif inject_fault == "timeout":
        engine.fault_injector.add_rule("run_python_code", FaultType.TIMEOUT, trigger_on_call_count=1)
    elif inject_fault == "irrelevant":
        engine.fault_injector.add_rule("search_web", FaultType.IRRELEVANT_RESULT, trigger_on_call_count=1)

    renderer.render_header(task)
    trace = engine.run(task)
    renderer.render_summary(trace)
    return trace


if __name__ == "__main__":
    task_input = (
        "Debug and fix the following recursive Fibonacci function that is failing:\n"
        "```python\n"
        "def fib(n):\n"
        "    return fib(n - 1) + fib(n - 2)\n"
        "print(fib(5))\n"
        "```"
    )
    run_cli_session(task_input)
