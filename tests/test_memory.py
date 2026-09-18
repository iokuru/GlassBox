import pytest
from glassbox.memory import AgentMemory
from glassbox.types import Action, Observation, StepRecord, Thought


def test_memory_step_tracking():
    memory = AgentMemory(max_working_steps=3)
    for i in range(5):
        step = StepRecord(
            step_number=i + 1,
            thought=Thought(content=f"Thought {i}"),
            action=Action(tool="run_python_code", params={"step": i}),
            observation=Observation(content=f"Obs {i}"),
        )
        memory.add_step(step)

    assert len(memory.steps) == 5
    assert len(memory.get_working_context()) == 3
    assert memory.get_working_context()[0].step_number == 3


def test_memory_history_formatting():
    memory = AgentMemory()
    step = StepRecord(
        step_number=1,
        thought=Thought(content="Checking code"),
        action=Action(tool="search_web", params={"query": "test"}),
        observation=Observation(content="Found results"),
    )
    memory.add_step(step)
    memory.record_hypothesis_failure("Hypothesis A", "Invalid type")

    history_text = memory.format_history_for_prompt()
    assert "Step 1" in history_text
    assert "Checking code" in history_text
    assert "Hypothesis A" in history_text
