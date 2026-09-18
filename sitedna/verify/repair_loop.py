from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from sitedna.verify.visual_diff import VisualDiffScorer
from sitedna.verify.palette_diff import PaletteDriftScorer
from sitedna.verify.motion_diff import MotionFidelityScorer
from sitedna.verify.layout_iou import LayoutIoUScorer


@dataclass
class RepairTask:
    region: str
    issue: str
    severity: str
    suggested_fix: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationResult:
    ssim: float
    psnr: float
    palette_mean_de: float
    layout_mean_iou: float
    motion_fidelity: float
    overall_score: float
    passed: bool
    repair_tasks: List[RepairTask] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    def summary_line(self) -> str:
        grade = (
            "A" if self.overall_score >= 0.9
            else "B" if self.overall_score >= 0.75
            else "C" if self.overall_score >= 0.6
            else "D" if self.overall_score >= 0.45
            else "F"
        )
        status = "PASS" if self.passed else "FAIL"
        return (
            f"[{status}] Grade={grade} "
            f"SSIM={self.ssim:.2f} "
            f"Palette={self.palette_mean_de:.1f}ΔE "
            f"Layout={self.layout_mean_iou:.0%} "
            f"Motion={self.motion_fidelity:.0%}"
        )


class CloseLoopVerifier:
    def __init__(
        self,
        ssim_threshold: float = 0.75,
        palette_de_threshold: float = 10.0,
        layout_iou_threshold: float = 0.5,
        motion_threshold: float = 0.6,
        max_repair_iterations: int = 5,
    ) -> None:
        self.ssim_threshold = ssim_threshold
        self.palette_de_threshold = palette_de_threshold
        self.layout_iou_threshold = layout_iou_threshold
        self.motion_threshold = motion_threshold
        self.max_repair_iterations = max_repair_iterations

        self._visual_scorer = VisualDiffScorer(threshold_ssim=ssim_threshold)
        self._palette_scorer = PaletteDriftScorer()
        self._motion_scorer = MotionFidelityScorer()
        self._layout_scorer = LayoutIoUScorer(threshold=layout_iou_threshold)

    def verify(
        self,
        reference_screenshot: Any,
        candidate_screenshot: Any,
        reference_palette: Optional[List[Dict]] = None,
        candidate_palette: Optional[List[Dict]] = None,
        reference_motion: Optional[Dict] = None,
        candidate_motion: Optional[Dict] = None,
        reference_dom: Optional[Dict] = None,
        candidate_dom: Optional[Dict] = None,
    ) -> VerificationResult:
        visual_result = self._visual_scorer.score(reference_screenshot, candidate_screenshot)

        palette_result = {"mean_delta_e": 0.0, "passed": True}
        if reference_palette and candidate_palette:
            palette_result = self._palette_scorer.score(reference_palette, candidate_palette)

        motion_result = {"overall": 1.0, "passed": True}
        if reference_motion and candidate_motion:
            motion_result = self._motion_scorer.score(reference_motion, candidate_motion)

        layout_result = {"mean_iou": 1.0, "passed": True}
        if reference_dom and candidate_dom:
            layout_result = self._layout_scorer.score(reference_dom, candidate_dom)

        ssim = visual_result.get("ssim", 0.0)
        palette_de = palette_result.get("mean_delta_e", 0.0)
        layout_iou = layout_result.get("mean_iou", 1.0)
        motion_fidelity = motion_result.get("overall", 1.0)

        # Weighted overall score
        overall = (
            ssim * 0.4
            + (1.0 - min(1.0, palette_de / 20.0)) * 0.2
            + layout_iou * 0.2
            + motion_fidelity * 0.2
        )

        passed = (
            ssim >= self.ssim_threshold
            and palette_de <= self.palette_de_threshold
            and layout_iou >= self.layout_iou_threshold
            and motion_fidelity >= self.motion_threshold
        )

        repair_tasks = self._emit_repair_tasks(visual_result, palette_result, motion_result, layout_result)

        return VerificationResult(
            ssim=ssim,
            psnr=visual_result.get("psnr", 0.0),
            palette_mean_de=palette_de,
            layout_mean_iou=layout_iou,
            motion_fidelity=motion_fidelity,
            overall_score=round(overall, 3),
            passed=passed,
            repair_tasks=repair_tasks,
            raw={
                "visual": visual_result,
                "palette": palette_result,
                "motion": motion_result,
                "layout": layout_result,
            },
        )

    def _emit_repair_tasks(
        self,
        visual: Dict,
        palette: Dict,
        motion: Dict,
        layout: Dict,
    ) -> List[RepairTask]:
        tasks: List[RepairTask] = []

        for region in visual.get("regions", [])[:3]:
            if region.get("severity") in ("high", "medium"):
                tasks.append(RepairTask(
                    region=f"visual:row{region['row']}_col{region['col']}",
                    issue=f"high pixel error ({region['error']:.3f}) in viewport region",
                    severity=region["severity"],
                    suggested_fix="Inspect background color, image alignment, or font rendering in this region",
                    metadata={"bbox": region.get("bbox")},
                ))

        for pair in palette.get("pairs", []):
            if not pair.get("acceptable"):
                tasks.append(RepairTask(
                    region=f"palette:{pair['reference_role']}",
                    issue=f"color drift ΔE={pair['delta_e']} for role {pair['reference_role']}",
                    severity="high" if pair["delta_e"] > 20 else "medium",
                    suggested_fix=f"Replace {pair['matched_hex']} with {pair['reference_hex']}",
                    metadata={"reference_hex": pair["reference_hex"], "found_hex": pair["matched_hex"]},
                ))

        for mismatch in motion.get("entry_animations", {}).get("mismatches", [])[:2]:
            tasks.append(RepairTask(
                region=f"motion:{mismatch['target']}",
                issue=mismatch.get("issue", "animation missing"),
                severity=mismatch.get("severity", "medium"),
                suggested_fix=f"Add or fix Framer Motion variant for target: {mismatch['target']}",
            ))

        for sec in layout.get("section_ious", []):
            if not sec.get("passed"):
                tasks.append(RepairTask(
                    region=f"layout:{sec['ref_id']}",
                    issue=f"section bounding box IoU={sec['iou']:.2f} below threshold",
                    severity="medium",
                    suggested_fix=f"Fix height or positioning of section '{sec['ref_id']}'",
                ))

        return tasks

    def format_full_report(self, result: VerificationResult) -> str:
        lines = [
            "=" * 55,
            "  GLASSBOX VISUAL VERIFICATION REPORT",
            "=" * 55,
            result.summary_line(),
            "",
            self._visual_scorer.format_report(result.raw.get("visual", {})),
            "",
            self._palette_scorer.__class__.__name__ + " (Palette ΔE)",
        ]
        palette_raw = result.raw.get("palette", {})
        lines.append(f"  Mean ΔE: {palette_raw.get('mean_delta_e', 0):.1f}  {'PASS' if palette_raw.get('passed') else 'FAIL'}")

        if result.repair_tasks:
            lines += ["", "Repair Tasks:"]
            for task in result.repair_tasks[:5]:
                lines.append(f"  [{task.severity.upper()[:1]}] {task.region}: {task.issue}")
                lines.append(f"        Fix: {task.suggested_fix}")

        lines.append("=" * 55)
        return "\n".join(lines)
