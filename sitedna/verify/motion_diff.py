from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def compare_entry_animations(
    reference: List[Dict], candidate: List[Dict]
) -> Dict[str, Any]:
    if not reference:
        return {"score": 1.0, "matched": 0, "total": 0, "mismatches": []}

    matched = 0
    mismatches = []
    cand_targets = {a.get("target", ""): a for a in candidate}

    for ref_anim in reference:
        target = ref_anim.get("target", "")
        cand_anim = cand_targets.get(target)

        if cand_anim is None:
            mismatches.append({
                "target": target,
                "issue": "missing animation entirely",
                "severity": "high",
            })
            continue

        ref_duration = ref_anim.get("duration", 0.5)
        cand_duration = cand_anim.get("duration", 0.5)
        duration_ok = abs(ref_duration - cand_duration) / max(ref_duration, 0.001) < 0.3

        ref_props = set(ref_anim.get("props", {}).keys()) if isinstance(ref_anim.get("props"), dict) else set()
        cand_props = set(cand_anim.get("props", {}).keys()) if isinstance(cand_anim.get("props"), dict) else set()
        props_ok = len(ref_props & cand_props) > 0

        if duration_ok and props_ok:
            matched += 1
        else:
            issues = []
            if not duration_ok:
                issues.append(f"duration mismatch: expected {ref_duration:.2f}s got {cand_duration:.2f}s")
            if not props_ok:
                issues.append(f"missing props: {ref_props - cand_props}")
            mismatches.append({
                "target": target,
                "issue": "; ".join(issues),
                "severity": "medium",
            })

    score = matched / len(reference) if reference else 1.0
    return {
        "score": round(score, 3),
        "matched": matched,
        "total": len(reference),
        "mismatches": mismatches,
    }


def compare_scroll_animations(
    reference: List[Dict], candidate: List[Dict]
) -> Dict[str, Any]:
    if not reference:
        return {"score": 1.0, "matched": 0, "total": 0, "coefficient_errors": []}

    matched = 0
    coefficient_errors = []
    cand_by_target = {a.get("target", ""): a for a in candidate}

    for ref_anim in reference:
        target = ref_anim.get("target", "")
        cand_anim = cand_by_target.get(target)

        if cand_anim is None:
            coefficient_errors.append({
                "target": target,
                "issue": "scroll animation not reproduced",
                "severity": "high",
            })
            continue

        ref_coeff = ref_anim.get("coefficient", 0)
        cand_coeff = cand_anim.get("coefficient", 0)

        if ref_coeff == 0:
            matched += 1
            continue

        rel_error = abs(ref_coeff - cand_coeff) / abs(ref_coeff)
        if rel_error < 0.2:
            matched += 1
        else:
            coefficient_errors.append({
                "target": target,
                "expected_coefficient": ref_coeff,
                "found_coefficient": cand_coeff,
                "relative_error": round(rel_error, 3),
                "severity": "medium" if rel_error < 0.5 else "high",
            })

    score = matched / len(reference) if reference else 1.0
    return {
        "score": round(score, 3),
        "matched": matched,
        "total": len(reference),
        "coefficient_errors": coefficient_errors,
    }


class MotionFidelityScorer:
    def score(
        self,
        reference_motion: Dict[str, Any],
        candidate_motion: Dict[str, Any],
    ) -> Dict[str, Any]:
        entry_result = compare_entry_animations(
            reference_motion.get("entry", []),
            candidate_motion.get("entry", []),
        )
        scroll_result = compare_scroll_animations(
            reference_motion.get("scroll_linked", []),
            candidate_motion.get("scroll_linked", []),
        )

        ref_parallax = len(reference_motion.get("mouse_parallax", []))
        cand_parallax = len(candidate_motion.get("mouse_parallax", []))
        parallax_score = min(1.0, cand_parallax / max(ref_parallax, 1))

        overall = (
            entry_result["score"] * 0.4
            + scroll_result["score"] * 0.4
            + parallax_score * 0.2
        )

        return {
            "overall": round(overall, 3),
            "entry_animations": entry_result,
            "scroll_linked": scroll_result,
            "mouse_parallax_score": round(parallax_score, 3),
            "passed": overall >= 0.6,
        }

    def format_report(self, result: Dict[str, Any]) -> str:
        passed = "PASS" if result.get("passed") else "FAIL"
        overall = result.get("overall", 0)
        bar_filled = int(overall * 20)
        bar = "#" * bar_filled + "." * (20 - bar_filled)

        lines = [
            f"Motion Fidelity: [{passed}]",
            f"  Overall [{bar}] {overall:.1%}",
            f"  Entry   {result.get('entry_animations', {}).get('score', 0):.1%}  "
            f"({result.get('entry_animations', {}).get('matched', 0)}/"
            f"{result.get('entry_animations', {}).get('total', 0)} matched)",
            f"  Scroll  {result.get('scroll_linked', {}).get('score', 0):.1%}  "
            f"({result.get('scroll_linked', {}).get('matched', 0)}/"
            f"{result.get('scroll_linked', {}).get('total', 0)} matched)",
            f"  Parallax {result.get('mouse_parallax_score', 0):.1%}",
        ]
        return "\n".join(lines)
