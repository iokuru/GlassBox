from __future__ import annotations

from typing import List, Optional, Set
from glassbox.types import Action, FailureRecord, FailureType, StepRecord


class LoopDetector:
    def __init__(self, repetition_threshold: int = 2, similarity_threshold: float = 0.85) -> None:
        self.repetition_threshold = repetition_threshold
        self.similarity_threshold = similarity_threshold

    def calculate_similarity(self, text_a: str, text_b: str) -> float:
        tokens_a = set(text_a.lower().split())
        tokens_b = set(text_b.lower().split())
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = tokens_a.intersection(tokens_b)
        union = tokens_a.union(tokens_b)
        return len(intersection) / len(union)

    def check_for_loop(self, steps: List[StepRecord], next_action: Action) -> Optional[FailureRecord]:
        if not steps:
            return None

        # 1. Exact or near-identical signature repetition
        curr_sig = next_action.signature()
        consecutive_matches = 0

        for step in reversed(steps):
            if step.action:
                prev_sig = step.action.signature()
                sim = self.calculate_similarity(curr_sig, prev_sig)
                if curr_sig == prev_sig or sim >= self.similarity_threshold:
                    consecutive_matches += 1
                else:
                    break

        if consecutive_matches >= self.repetition_threshold:
            return FailureRecord(
                failure_type=FailureType.LOOP_DETECTED,
                description=f"Action '{next_action.tool}' repeated {consecutive_matches + 1} times with identical or stagnant arguments.",
                error_signature=f"Loop:{next_action.tool}",
                attempt_count=consecutive_matches + 1,
            )

        # 2. Cycle detection (e.g. A -> B -> A -> B)
        recent_actions = [s.action.tool for s in steps if s.action]
        recent_actions.append(next_action.tool)

        if len(recent_actions) >= 4:
            last_4 = recent_actions[-4:]
            if last_4[0] == last_4[2] and last_4[1] == last_4[3] and last_4[0] != last_4[1]:
                return FailureRecord(
                    failure_type=FailureType.LOOP_DETECTED,
                    description=f"Cyclical oscillation detected between tools '{last_4[0]}' and '{last_4[1]}'.",
                    error_signature=f"Cycle:{last_4[0]}<->{last_4[1]}",
                    attempt_count=2,
                )

        return None
