from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sitedna.capture.palette import parse_css_color, rgb_to_oklch


def delta_e_cie2000(lab1: Tuple[float, float, float], lab2: Tuple[float, float, float]) -> float:
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    kL, kC, kH = 1.0, 1.0, 1.0

    avg_L = (L1 + L2) / 2.0
    C1 = math.sqrt(a1 ** 2 + b1 ** 2)
    C2 = math.sqrt(a2 ** 2 + b2 ** 2)
    avg_C = (C1 + C2) / 2.0
    G = 0.5 * (1 - math.sqrt(avg_C ** 7 / (avg_C ** 7 + 25 ** 7)))
    a1p = a1 * (1 + G)
    a2p = a2 * (1 + G)
    C1p = math.sqrt(a1p ** 2 + b1 ** 2)
    C2p = math.sqrt(a2p ** 2 + b2 ** 2)

    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360

    dLp = L2 - L1
    dCp = C2p - C1p
    if C1p * C2p == 0:
        dhp = 0.0
    elif abs(h2p - h1p) <= 180:
        dhp = h2p - h1p
    elif h2p - h1p > 180:
        dhp = h2p - h1p - 360
    else:
        dhp = h2p - h1p + 360

    dHp = 2.0 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp / 2.0))

    avg_Lp = (L1 + L2) / 2.0
    avg_Cp = (C1p + C2p) / 2.0
    if C1p * C2p == 0:
        avg_hp = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        avg_hp = (h1p + h2p) / 2.0
    elif h1p + h2p < 360:
        avg_hp = (h1p + h2p + 360) / 2.0
    else:
        avg_hp = (h1p + h2p - 360) / 2.0

    T = (
        1
        - 0.17 * math.cos(math.radians(avg_hp - 30))
        + 0.24 * math.cos(math.radians(2 * avg_hp))
        + 0.32 * math.cos(math.radians(3 * avg_hp + 6))
        - 0.20 * math.cos(math.radians(4 * avg_hp - 63))
    )

    SL = 1 + 0.015 * (avg_Lp - 50) ** 2 / math.sqrt(20 + (avg_Lp - 50) ** 2)
    SC = 1 + 0.045 * avg_Cp
    SH = 1 + 0.015 * avg_Cp * T
    d_theta = 30 * math.exp(-((avg_hp - 275) / 25) ** 2)
    RC = 2 * math.sqrt(avg_Cp ** 7 / (avg_Cp ** 7 + 25 ** 7))
    RT = -math.sin(math.radians(2 * d_theta)) * RC

    return math.sqrt(
        (dLp / (kL * SL)) ** 2
        + (dCp / (kC * SC)) ** 2
        + (dHp / (kH * SH)) ** 2
        + RT * (dCp / (kC * SC)) * (dHp / (kH * SH))
    )


def oklch_to_lab_approx(L: float, C: float, H: float) -> Tuple[float, float, float]:
    a = C * math.cos(math.radians(H))
    b = C * math.sin(math.radians(H))
    return (L * 100, a * 200, b * 200)


class PaletteDriftScorer:
    def score(
        self,
        reference_palette: List[Dict[str, Any]],
        candidate_palette: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not reference_palette or not candidate_palette:
            return {
                "mean_delta_e": 999.0,
                "max_delta_e": 999.0,
                "passed": False,
                "pairs": [],
                "error": "Empty palette(s)",
            }

        ref_labs = self._palette_to_lab(reference_palette)
        cand_labs = self._palette_to_lab(candidate_palette)

        pairs = []
        for ref_entry, ref_lab in ref_labs:
            best_delta = None
            best_match = None
            for cand_entry, cand_lab in cand_labs:
                delta = delta_e_cie2000(ref_lab, cand_lab)
                if best_delta is None or delta < best_delta:
                    best_delta = delta
                    best_match = cand_entry

            if best_delta is not None and best_match is not None:
                pairs.append({
                    "reference_role": ref_entry.get("role", "?"),
                    "reference_hex": ref_entry.get("hex", "#000"),
                    "matched_hex": best_match.get("hex", "#000"),
                    "delta_e": round(best_delta, 2),
                    "acceptable": best_delta < 10.0,
                })

        delta_es = [p["delta_e"] for p in pairs]
        mean_de = sum(delta_es) / len(delta_es) if delta_es else 999.0
        max_de = max(delta_es) if delta_es else 999.0

        return {
            "mean_delta_e": round(mean_de, 2),
            "max_delta_e": round(max_de, 2),
            "passed": mean_de < 10.0,
            "pairs": pairs,
        }

    def _palette_to_lab(
        self, palette: List[Dict[str, Any]]
    ) -> List[Tuple[Dict, Tuple[float, float, float]]]:
        result = []
        for entry in palette:
            oklch_str = entry.get("oklch", "")
            parts = oklch_str.split()
            if len(parts) == 3:
                try:
                    L, C, H = float(parts[0]), float(parts[1]), float(parts[2])
                    lab = oklch_to_lab_approx(L, C, H)
                    result.append((entry, lab))
                    continue
                except ValueError:
                    pass

            hex_val = entry.get("hex", "#808080")
            rgb = parse_css_color(hex_val) or (128, 128, 128)
            L_val, C_val, H_val = rgb_to_oklch(*rgb)
            lab = oklch_to_lab_approx(L_val, C_val, H_val)
            result.append((entry, lab))

        return result
