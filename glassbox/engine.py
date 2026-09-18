from __future__ import annotations

import time
import uuid
from typing import Callable, List, Optional

from glassbox.config import AgentConfig
from glassbox.failure.classifier import FailureClassifier
from glassbox.failure.injection import FaultInjector
from glassbox.failure.loop_detector import LoopDetector
from glassbox.failure.recovery import RecoveryEngine
from glassbox.memory import AgentMemory
from glassbox.planner import Planner
from glassbox.provider import BaseLLMProvider, MockDebuggingProvider, OpenAICompatibleProvider
from glassbox.tool_registry import ToolRegistry
from glassbox.tools.code_sandbox import CodeSandboxTool
from glassbox.tools.doc_store import DocStoreTool
from glassbox.tools.web_search import WebSearchTool
from glassbox.types import (
    Action,
    AgentStatus,
    ExecutionTrace,
    FailureRecord,
    FailureType,
    Observation,
    RecoveryAction,
    RecoveryRecord,
    StepRecord,
    Thought,
)


class AgentEngine:
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        provider: Optional[BaseLLMProvider] = None,
        registry: Optional[ToolRegistry] = None,
    ) -> None:
        self.config = config or AgentConfig()
        self.registry = registry or self._build_default_registry()
        self.provider = provider or self._build_provider(self.config)
        self.planner = Planner(self.provider, self.registry)
        self.classifier = FailureClassifier()
        self.loop_detector = LoopDetector(similarity_threshold=self.config.loop_similarity_threshold)
        self.recovery_engine = RecoveryEngine(max_retries=self.config.max_retries_per_failure)
        self.fault_injector = FaultInjector()

        # Telemetry callbacks for live stream UI
        self.on_step_start: Optional[Callable[[int], None]] = None
        self.on_thought: Optional[Callable[[Thought], None]] = None
        self.on_action: Optional[Callable[[Action], None]] = None
        self.on_observation: Optional[Callable[[Observation], None]] = None
        self.on_failure: Optional[Callable[[FailureRecord], None]] = None
        self.on_recovery: Optional[Callable[[RecoveryRecord], None]] = None
        self.on_step_complete: Optional[Callable[[StepRecord], None]] = None

    def _build_default_registry(self) -> ToolRegistry:
        reg = ToolRegistry()
        sandbox = CodeSandboxTool()
        search = WebSearchTool()
        doc_store = DocStoreTool()

        reg.register(
            name="run_python_code",
            description="Run Python code in a safe sandbox. Use to test hypotheses or run fixes.",
        )(sandbox.run_python_code)

        reg.register(
            name="search_web",
            description="Search developer docs and error databases for solutions.",
        )(search.search_web)

        reg.register(
            name="lookup_documentation",
            description="Lookup official standard library docs and signatures.",
        )(doc_store.lookup_documentation)

        return reg

    def _build_provider(self, config: AgentConfig) -> BaseLLMProvider:
        if config.api_key:
            return OpenAICompatibleProvider(
                api_key=config.api_key,
                base_url=config.api_base_url,
                model=config.model_name,
            )
        return MockDebuggingProvider()

    def run(self, task: str) -> ExecutionTrace:
        session_id = str(uuid.uuid4())[:8]
        memory = AgentMemory()
        start_wall_time = time.time()
        active_recovery_prompt: Optional[str] = None

        trace = ExecutionTrace(
            session_id=session_id,
            task=task,
            status=AgentStatus.RUNNING,
        )

        step_counter = 0

        while step_counter < self.config.max_steps:
            elapsed_total = time.time() - start_wall_time
            if elapsed_total > self.config.timeout_seconds:
                trace.status = AgentStatus.BUDGET_EXHAUSTED
                trace.final_answer = f"Task timed out after {elapsed_total:.2f} seconds (budget limit)."
                break

            step_counter += 1
            step_start = time.perf_counter()

            if self.on_step_start:
                self.on_step_start(step_counter)

            # 1. Decide next step
            history_str = memory.format_history_for_prompt()
            thought, action, is_done, final_ans = self.planner.decide_next_step(
                task=task,
                history_context=history_str,
                recovery_directive=active_recovery_prompt,
            )

            if self.on_thought:
                self.on_thought(thought)

            # Check if agent marked task completed
            if is_done or not action:
                trace.status = AgentStatus.SUCCEEDED
                trace.final_answer = final_ans or "Task finished."
                step_record = StepRecord(
                    step_number=step_counter,
                    thought=thought,
                    action=None,
                    observation=Observation(content=final_ans or "Goal accomplished.", is_error=False),
                    duration_ms=(time.perf_counter() - step_start) * 1000.0,
                )
                trace.steps.append(step_record)
                memory.add_step(step_record)
                if self.on_step_complete:
                    self.on_step_complete(step_record)
                break

            if self.on_action:
                self.on_action(action)

            # 2. Pre-execution Loop Detection
            loop_failure = self.loop_detector.check_for_loop(memory.steps, action)
            if loop_failure:
                trace.total_failures_encountered += 1
                if self.on_failure:
                    self.on_failure(loop_failure)

                available_tools = [t.name for t in self.registry.list_tools()]
                recovery_plan = self.recovery_engine.plan_recovery(
                    failure=loop_failure,
                    last_action=action,
                    available_tools=available_tools,
                    failure_history=memory.failure_history,
                )
                trace.total_recoveries_applied += 1
                if self.on_recovery:
                    self.on_recovery(recovery_plan)

                active_recovery_prompt = self.recovery_engine.generate_recovery_prompt(loop_failure, recovery_plan)

                obs = Observation(
                    content=f"Execution blocked: {loop_failure.description}",
                    is_error=True,
                    metadata={"error_type": "loop_detected"},
                )

                step_record = StepRecord(
                    step_number=step_counter,
                    thought=thought,
                    action=action,
                    observation=obs,
                    failure=loop_failure,
                    recovery=recovery_plan,
                    duration_ms=(time.perf_counter() - step_start) * 1000.0,
                )
                trace.steps.append(step_record)
                memory.add_step(step_record)
                if self.on_step_complete:
                    self.on_step_complete(step_record)
                continue

            # 3. Execution (with fault injection interception)
            def execute_tool() -> Observation:
                return self.registry.execute(action.tool, action.params)

            observation = self.fault_injector.intercept(action.tool, action.params, execute_tool)

            if self.on_observation:
                self.on_observation(observation)

            # 4. Post-execution Failure Classification & Recovery
            failure_rec: Optional[FailureRecord] = None
            recovery_rec: Optional[RecoveryRecord] = None

            if observation.is_error:
                failure_rec = self.classifier.classify(observation, action)
                if failure_rec:
                    trace.total_failures_encountered += 1
                    if self.on_failure:
                        self.on_failure(failure_rec)

                    available_tools = [t.name for t in self.registry.list_tools()]
                    recovery_rec = self.recovery_engine.plan_recovery(
                        failure=failure_rec,
                        last_action=action,
                        available_tools=available_tools,
                        failure_history=memory.failure_history,
                    )
                    trace.total_recoveries_applied += 1
                    if self.on_recovery:
                        self.on_recovery(recovery_rec)

                    if recovery_rec.strategy == RecoveryAction.ESCALATE_TO_USER:
                        trace.status = AgentStatus.ESCALATED
                        active_recovery_prompt = None
                    else:
                        active_recovery_prompt = self.recovery_engine.generate_recovery_prompt(failure_rec, recovery_rec)
            else:
                # Success clears active recovery directive
                active_recovery_prompt = None

            step_record = StepRecord(
                step_number=step_counter,
                thought=thought,
                action=action,
                observation=observation,
                failure=failure_rec,
                recovery=recovery_rec,
                duration_ms=(time.perf_counter() - step_start) * 1000.0,
            )
            trace.steps.append(step_record)
            memory.add_step(step_record)

            if self.on_step_complete:
                self.on_step_complete(step_record)

            if trace.status == AgentStatus.ESCALATED:
                trace.final_answer = "Escalated to user after repeated unrecoverable failures."
                break

        if step_counter >= self.config.max_steps and trace.status == AgentStatus.RUNNING:
            trace.status = AgentStatus.BUDGET_EXHAUSTED
            trace.final_answer = f"Agent reached step budget limit ({self.config.max_steps} steps)."

        trace.total_duration_ms = (time.time() - start_wall_time) * 1000.0
        return trace
