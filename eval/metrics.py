from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BenchmarkMetrics:
    visual_ssim: float = 0.0
    palette_delta_e: float = 999.0
    layout_iou: float = 0.0
    motion_fidelity: float = 0.0
    overall_score: float = 0.0

    failure_f1: float = 0.0
    recovery_success_rate: float = 0.0
    unresolved_honesty: float = 0.0

    capture_duration_s: float = 0.0
    repair_iterations: int = 0
    steps_used: int = 0
    budget_used_pct: float = 0.0

    passed: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def grade(self) -> str:
        s = self.overall_score
        if s >= 0.90: return "A"
        if s >= 0.75: return "B"
        if s >= 0.60: return "C"
        if s >= 0.45: return "D"
        return "F"

    def to_row(self) -> Dict[str, Any]:
        return {
            "grade": self.grade(),
            "overall": round(self.overall_score, 3),
            "ssim": round(self.visual_ssim, 3),
            "palette_de": round(self.palette_delta_e, 1),
            "layout_iou": round(self.layout_iou, 3),
            "motion": round(self.motion_fidelity, 3),
            "fail_f1": round(self.failure_f1, 3),
            "recovery": round(self.recovery_success_rate, 3),
            "honesty": round(self.unresolved_honesty, 3),
            "iterations": self.repair_iterations,
            "steps": self.steps_used,
        }


def compute_failure_f1(
    true_failures: List[str], detected_failures: List[str]
) -> float:
    if not true_failures and not detected_failures:
        return 1.0
    tp = len(set(true_failures) & set(detected_failures))
    fp = len(set(detected_failures) - set(true_failures))
    fn = len(set(true_failures) - set(detected_failures))
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def compute_recovery_success_rate(
    injected_failures: List[str], recovered: List[str]
) -> float:
    if not injected_failures:
        return 1.0
    return len(set(recovered)) / len(set(injected_failures))


def compute_honesty_score(
    unresolved_count: int, total_tasks: int, self_reported_unresolved: int
) -> float:
    if total_tasks == 0:
        return 1.0
    if unresolved_count == 0:
        return 1.0 if self_reported_unresolved == 0 else 0.5
    return min(1.0, self_reported_unresolved / unresolved_count)
