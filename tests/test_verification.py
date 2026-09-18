import pytest
import numpy as np
from sitedna.verify.visual_diff import VisualDiffScorer, ssim_score, mse_score, psnr_score, load_image
from sitedna.verify.palette_diff import PaletteDriftScorer, delta_e_cie2000, oklch_to_lab_approx
from sitedna.verify.motion_diff import MotionFidelityScorer, compare_entry_animations
from sitedna.verify.layout_iou import LayoutIoUScorer, box_iou
from sitedna.verify.repair_loop import CloseLoopVerifier


def make_image(h=100, w=100, fill=0.5) -> np.ndarray:
    return np.full((h, w, 3), fill, dtype=np.float32)


def test_ssim_identical_images():
    img = make_image(fill=0.5)
    score = ssim_score(img, img)
    assert score > 0.99


def test_ssim_different_images():
    img_a = make_image(fill=0.1)
    img_b = make_image(fill=0.9)
    score = ssim_score(img_a, img_b)
    assert score < 0.5


def test_mse_zero_for_identical():
    img = make_image()
    assert mse_score(img, img) == pytest.approx(0.0)


def test_psnr_high_for_identical():
    img = make_image()
    assert psnr_score(img, img) > 50


def test_visual_diff_scorer_pass():
    img = make_image(fill=0.5)
    scorer = VisualDiffScorer(threshold_ssim=0.75)
    result = scorer.score(img, img)
    assert result["passed"] is True
    assert result["ssim"] > 0.99


def test_visual_diff_scorer_fail():
    img_a = make_image(fill=0.1)
    img_b = make_image(fill=0.9)
    scorer = VisualDiffScorer(threshold_ssim=0.75)
    result = scorer.score(img_a, img_b)
    assert result["passed"] is False


def test_visual_diff_scorer_report():
    img = make_image()
    scorer = VisualDiffScorer(threshold_ssim=0.75)
    result = scorer.score(img, img)
    report = scorer.format_report(result)
    assert "SSIM" in report or "Visual" in report


def test_delta_e_identical_colors():
    lab = (50.0, 0.0, 0.0)
    assert delta_e_cie2000(lab, lab) == pytest.approx(0.0, abs=0.001)


def test_delta_e_different_colors():
    lab_a = (50.0, 50.0, 50.0)
    lab_b = (10.0, -30.0, -30.0)
    assert delta_e_cie2000(lab_a, lab_b) > 5.0


def test_palette_drift_scorer_identical():
    palette = [
        {"role": "bg.base", "oklch": "0.18 0.01 260", "hex": "#141517"},
        {"role": "fg.primary", "oklch": "0.96 0.01 90", "hex": "#f4f1ea"},
    ]
    scorer = PaletteDriftScorer()
    result = scorer.score(palette, palette)
    assert result["mean_delta_e"] < 2.0
    assert result["passed"] is True


def test_palette_drift_scorer_empty():
    scorer = PaletteDriftScorer()
    result = scorer.score([], [])
    assert result["passed"] is False


def test_box_iou_identical():
    box = (0, 0, 100, 100)
    assert box_iou(box, box) == pytest.approx(1.0)


def test_box_iou_no_overlap():
    box_a = (0, 0, 50, 50)
    box_b = (100, 100, 200, 200)
    assert box_iou(box_a, box_b) == pytest.approx(0.0)


def test_box_iou_partial():
    box_a = (0, 0, 100, 100)
    box_b = (50, 0, 150, 100)
    iou = box_iou(box_a, box_b)
    assert 0.2 < iou < 0.6


def test_layout_iou_scorer_identical():
    dom = {
        "sections": [
            {"id": "hero", "rect": {"x": 0, "y": 0, "w": 1440, "h": 900}},
            {"id": "content", "rect": {"x": 0, "y": 900, "w": 1440, "h": 540}},
        ]
    }
    scorer = LayoutIoUScorer(threshold=0.5)
    result = scorer.score(dom, dom)
    assert result["mean_iou"] > 0.9
    assert result["passed"] is True


def test_compare_entry_animations_match():
    ref = [{"target": "hero", "props": {"opacity": ["0", "1"]}, "duration": 0.7}]
    cand = [{"target": "hero", "props": {"opacity": ["0", "1"]}, "duration": 0.7}]
    result = compare_entry_animations(ref, cand)
    assert result["matched"] == 1
    assert result["score"] == pytest.approx(1.0)


def test_motion_scorer_empty_motion():
    scorer = MotionFidelityScorer()
    result = scorer.score({}, {})
    assert result["overall"] >= 0.6
    assert result["passed"] is True


def test_close_loop_verifier_identical():
    img = make_image(fill=0.5)
    palette = [
        {"role": "bg.base", "oklch": "0.18 0.01 260", "hex": "#141517"},
    ]
    verifier = CloseLoopVerifier(ssim_threshold=0.75)
    result = verifier.verify(
        reference_screenshot=img,
        candidate_screenshot=img,
        reference_palette=palette,
        candidate_palette=palette,
    )
    assert result.ssim > 0.99
    assert result.passed is True


def test_close_loop_verifier_report():
    img = make_image(fill=0.5)
    verifier = CloseLoopVerifier(ssim_threshold=0.75)
    result = verifier.verify(img, img)
    report = verifier.format_full_report(result)
    assert "GLASSBOX" in report
    assert "SSIM" in report
