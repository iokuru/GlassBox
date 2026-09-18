from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image


def load_image(source: Any) -> Optional[np.ndarray]:
    if source is None:
        return None
    if isinstance(source, bytes):
        import io
        img = Image.open(io.BytesIO(source)).convert("RGB")
        return np.array(img, dtype=np.float32) / 255.0
    if isinstance(source, str):
        img = Image.open(source).convert("RGB")
        return np.array(img, dtype=np.float32) / 255.0
    if isinstance(source, np.ndarray):
        return source.astype(np.float32) / 255.0 if source.max() > 1.0 else source.astype(np.float32)
    return None


def resize_to_match(img_a: np.ndarray, img_b: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    ha, wa = img_a.shape[:2]
    hb, wb = img_b.shape[:2]
    if ha == hb and wa == wb:
        return img_a, img_b

    target_h = min(ha, hb)
    target_w = min(wa, wb)

    def resize_np(img: np.ndarray, h: int, w: int) -> np.ndarray:
        pil = Image.fromarray((img * 255).astype(np.uint8)).resize((w, h), Image.LANCZOS)
        return np.array(pil, dtype=np.float32) / 255.0

    return resize_np(img_a, target_h, target_w), resize_np(img_b, target_h, target_w)


def ssim_score(img_a: np.ndarray, img_b: np.ndarray) -> float:
    try:
        from skimage.metrics import structural_similarity
        a_gray = np.mean(img_a, axis=2) if img_a.ndim == 3 else img_a
        b_gray = np.mean(img_b, axis=2) if img_b.ndim == 3 else img_b
        score, _ = structural_similarity(a_gray, b_gray, full=True, data_range=1.0)
        return float(score)
    except ImportError:
        return _naive_ssim(img_a, img_b)


def _naive_ssim(img_a: np.ndarray, img_b: np.ndarray) -> float:
    mu_a = img_a.mean()
    mu_b = img_b.mean()
    sigma_a = img_a.std()
    sigma_b = img_b.std()
    sigma_ab = ((img_a - mu_a) * (img_b - mu_b)).mean()
    c1, c2 = 0.01 ** 2, 0.03 ** 2
    numerator = (2 * mu_a * mu_b + c1) * (2 * sigma_ab + c2)
    denominator = (mu_a ** 2 + mu_b ** 2 + c1) * (sigma_a ** 2 + sigma_b ** 2 + c2)
    return float(numerator / (denominator + 1e-8))


def mse_score(img_a: np.ndarray, img_b: np.ndarray) -> float:
    return float(np.mean((img_a - img_b) ** 2))


def psnr_score(img_a: np.ndarray, img_b: np.ndarray) -> float:
    mse = mse_score(img_a, img_b)
    if mse == 0.0:
        return 100.0
    return float(10 * np.log10(1.0 / mse))


def compute_diff_heatmap(img_a: np.ndarray, img_b: np.ndarray) -> np.ndarray:
    diff = np.abs(img_a - img_b).mean(axis=2) if img_a.ndim == 3 else np.abs(img_a - img_b)
    return diff


def identify_worst_regions(
    heatmap: np.ndarray, grid_size: int = 6
) -> List[Dict[str, Any]]:
    h, w = heatmap.shape
    cell_h = h // grid_size
    cell_w = w // grid_size
    regions = []

    for row in range(grid_size):
        for col in range(grid_size):
            y0, y1 = row * cell_h, (row + 1) * cell_h
            x0, x1 = col * cell_w, (col + 1) * cell_w
            cell = heatmap[y0:y1, x0:x1]
            mean_error = float(cell.mean())
            regions.append({
                "row": row,
                "col": col,
                "bbox": [x0, y0, x1, y1],
                "error": round(mean_error, 4),
                "severity": "high" if mean_error > 0.15 else "medium" if mean_error > 0.08 else "low",
            })

    regions.sort(key=lambda r: r["error"], reverse=True)
    return regions[:8]


class VisualDiffScorer:
    def __init__(self, threshold_ssim: float = 0.75) -> None:
        self.threshold_ssim = threshold_ssim

    def score(
        self,
        reference: Any,
        candidate: Any,
    ) -> Dict[str, Any]:
        ref = load_image(reference)
        cand = load_image(candidate)

        if ref is None or cand is None:
            return {
                "ssim": 0.0,
                "mse": 1.0,
                "psnr": 0.0,
                "passed": False,
                "regions": [],
                "error": "Could not load images",
            }

        ref, cand = resize_to_match(ref, cand)
        ssim = ssim_score(ref, cand)
        mse = mse_score(ref, cand)
        psnr = psnr_score(ref, cand)
        heatmap = compute_diff_heatmap(ref, cand)
        worst_regions = identify_worst_regions(heatmap)

        return {
            "ssim": round(ssim, 4),
            "mse": round(mse, 6),
            "psnr": round(psnr, 2),
            "passed": ssim >= self.threshold_ssim,
            "regions": worst_regions,
            "heatmap": heatmap,
        }

    def format_report(self, result: Dict[str, Any]) -> str:
        passed = "PASS" if result.get("passed") else "FAIL"
        ssim = result.get("ssim", 0)
        psnr = result.get("psnr", 0)
        bar_filled = int(ssim * 20)
        bar = "#" * bar_filled + "." * (20 - bar_filled)
        report = [
            f"Visual Diff: [{passed}]",
            f"  SSIM  [{bar}] {ssim:.1%}",
            f"  PSNR  {psnr:.1f} dB",
        ]
        if result.get("regions"):
            top = result["regions"][0]
            report.append(f"  Worst region: row={top['row']} col={top['col']} error={top['error']:.3f}")
        return "\n".join(report)
