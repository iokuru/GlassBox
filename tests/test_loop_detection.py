import pytest
from glassbox.failure.loop_detector import LoopDetector
from glassbox.types import Action, FailureType, StepRecord, Thought


def test_jaccard_similarity_calculation():
    detector = LoopDetector()
    sim = detector.calculate_similarity("search error python", "search error python")
    assert sim == 1.0

    sim_partial = detector.calculate_similarity("search error python", "search bug python")
    assert 0.4 < sim_partial < 0.6

    sim_disjoint = detector.calculate_similarity("apple orange", "car truck")
    assert sim_disjoint == 0.0


def test_exact_repetition_loop_detection():
    detector = LoopDetector(repetition_threshold=2)
    action = Action(tool="search_web", params={"query": "recursion fix"})

    steps = [
        StepRecord(
            step_number=1,
            thought=Thought(content="search 1"),
            action=action,
        ),
        StepRecord(
            step_number=2,
            thought=Thought(content="search 2"),
            action=action,
        ),
    ]

    failure = detector.check_for_loop(steps, action)
    assert failure is not None
    assert failure.failure_type == FailureType.LOOP_DETECTED
    assert "repeated" in failure.description


def test_cycle_oscillation_detection():
    detector = LoopDetector()
    action_a = Action(tool="tool_a", params={})
    action_b = Action(tool="tool_b", params={})

    steps = [
        StepRecord(step_number=1, thought=Thought(content="a1"), action=action_a),
        StepRecord(step_number=2, thought=Thought(content="b1"), action=action_b),
        StepRecord(step_number=3, thought=Thought(content="a2"), action=action_a),
    ]

    # Candidate is action_b -> completes pattern A -> B -> A -> B
    failure = detector.check_for_loop(steps, action_b)
    assert failure is not None
    assert failure.failure_type == FailureType.LOOP_DETECTED
    assert "oscillation" in failure.description.lower()
