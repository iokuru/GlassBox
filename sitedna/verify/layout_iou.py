from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np


def compute_layout_iou(
    reference_sections: List[Dict], candidate_sections: List[Dict]
) -> Dict[str, Any]:
    if not reference_sections:
        return {"mean_iou": 1.0, "section_ious": [], "passed": True}

    section_ious = []

    for ref_sec in reference_sections:
        ref_rect = ref_sec.get("rect", {})
        ref_box = (
            ref_rect.get("x", 0),
            ref_rect.get("y", 0),
            ref_rect.get("x", 0) + ref_rect.get("w", 100),
            ref_rect.get("y", 0) + ref_rect.get("h", 100),
        )

        best_iou = 0.0
        best_match = None

        for cand_sec in candidate_sections:
            cand_rect = cand_sec.get("rect", {})
            cand_box = (
                cand_rect.get("x", 0),
                cand_rect.get("y", 0),
                cand_rect.get("x", 0) + cand_rect.get("w", 100),
                cand_rect.get("y", 0) + cand_rect.get("h", 100),
            )
            iou = box_iou(ref_box, cand_box)
            if iou > best_iou:
                best_iou = iou
                best_match = cand_sec.get("id", "?")

        section_ious.append({
            "ref_id": ref_sec.get("id", "?"),
            "best_match": best_match,
            "iou": round(best_iou, 3),
            "passed": best_iou >= 0.5,
        })

    mean_iou = sum(s["iou"] for s in section_ious) / len(section_ious) if section_ious else 0.0
    return {
        "mean_iou": round(mean_iou, 3),
        "section_ious": section_ious,
        "passed": mean_iou >= 0.5,
    }


def box_iou(
    box_a: Tuple[float, float, float, float],
    box_b: Tuple[float, float, float, float],
) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
        return 0.0

    inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
    area_a = max(0, (ax2 - ax1)) * max(0, (ay2 - ay1))
    area_b = max(0, (bx2 - bx1)) * max(0, (by2 - by1))
    union_area = area_a + area_b - inter_area

    return inter_area / union_area if union_area > 0 else 0.0


class LayoutIoUScorer:
    def __init__(self, threshold: float = 0.5) -> None:
        self.threshold = threshold

    def score(
        self,
        reference_dom: Dict[str, Any],
        candidate_dom: Dict[str, Any],
    ) -> Dict[str, Any]:
        ref_sections = reference_dom.get("sections", [])
        cand_sections = candidate_dom.get("sections", [])
        result = compute_layout_iou(ref_sections, cand_sections)
        result["passed"] = result["mean_iou"] >= self.threshold
        return result

    def format_report(self, result: Dict[str, Any]) -> str:
        passed = "PASS" if result.get("passed") else "FAIL"
        mean_iou = result.get("mean_iou", 0)
        bar_filled = int(mean_iou * 20)
        bar = "█" * bar_filled + "░" * (20 - bar_filled)
        lines = [
            f"Layout IoU: [{passed}]",
            f"  Mean [{bar}] {mean_iou:.1%}",
        ]
        for s in result.get("section_ious", [])[:4]:
            status = "OK" if s.get("passed") else "!!"
            lines.append(f"  [{status}] {s['ref_id']:20s} IoU={s['iou']:.2f}")
        return "\n".join(lines)
