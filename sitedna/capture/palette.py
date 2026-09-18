from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


def hex_to_rgb(hex_color: str) -> Optional[Tuple[int, int, int]]:
    hex_color = hex_color.strip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    if len(hex_color) != 6:
        return None
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return (r, g, b)
    except ValueError:
        return None


def parse_css_color(color_str: str) -> Optional[Tuple[int, int, int]]:
    if color_str.startswith("#"):
        return hex_to_rgb(color_str)

    m = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", color_str)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))

    return None


def rgb_to_oklch(r: int, g: int, b: int) -> Tuple[float, float, float]:
    # sRGB → linear
    def linearize(c: float) -> float:
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    rl, gl, bl = linearize(r), linearize(g), linearize(b)

    # linear sRGB → OKLab
    l_cone = 0.4122214708 * rl + 0.5363325363 * gl + 0.0514459929 * bl
    m_cone = 0.2119034982 * rl + 0.6806995451 * gl + 0.1073969566 * bl
    s_cone = 0.0883024619 * rl + 0.2817188376 * gl + 0.6299787005 * bl

    l_ = l_cone ** (1 / 3)
    m_ = m_cone ** (1 / 3)
    s_ = s_cone ** (1 / 3)

    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b_val = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_

    C = (a ** 2 + b_val ** 2) ** 0.5
    H = (360 + (180 / 3.14159) * (b_val and a and (b_val / a) and 0)) % 360

    import math
    H = math.degrees(math.atan2(b_val, a)) % 360

    return (round(L, 4), round(C, 4), round(H, 1))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def relative_luminance(r: int, g: int, b: int) -> float:
    def linearize(c: float) -> float:
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def wcag_contrast(rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
    l1 = relative_luminance(*rgb1)
    l2 = relative_luminance(*rgb2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def assign_color_role(rgb: Tuple[int, int, int], all_colors: List[Tuple]) -> str:
    r, g, b = rgb
    lum = relative_luminance(r, g, b)

    if lum < 0.05:
        return "bg.base"
    if lum < 0.15:
        return "bg.subtle"
    if lum > 0.85:
        return "fg.primary"
    if lum > 0.6:
        return "fg.muted"

    sat = max(r, g, b) - min(r, g, b)
    if sat > 80:
        if b > r and b > g:
            return "accent.blue"
        if r > g and r > b:
            return "accent.red"
        if g > r and g > b:
            return "accent.green"
        return "accent.primary"
    return "neutral"


class PaletteExtractor:
    def __init__(self, session: Any) -> None:
        self.session = session

    async def extract(self, raw_colors: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        if raw_colors is None:
            if not self.session.is_available():
                return self._mock_palette()
            raw_colors = []

        if not raw_colors:
            return self._mock_palette()

        parsed: List[Tuple[int, int, int]] = []
        for c in raw_colors:
            rgb = parse_css_color(c)
            if rgb and rgb not in parsed:
                parsed.append(rgb)

        if not parsed:
            return self._mock_palette()

        return self._build_palette(parsed)

    def _build_palette(self, colors: List[Tuple[int, int, int]]) -> List[Dict[str, Any]]:
        if len(colors) > 2:
            from sklearn.cluster import KMeans
            arr = np.array(colors, dtype=float)
            k = min(6, len(colors))
            km = KMeans(n_clusters=k, random_state=42, n_init=10)
            km.fit(arr)
            centroids = km.cluster_centers_.astype(int)
            colors = [tuple(c) for c in centroids]

        bg_rgb = min(colors, key=lambda c: relative_luminance(*c))
        palette = []
        seen_roles = set()

        for rgb in colors:
            r, g, b = rgb
            role = assign_color_role(rgb, colors)
            if role in seen_roles:
                role = f"{role}.{len(seen_roles)}"
            seen_roles.add(role)

            L, C, H = rgb_to_oklch(r, g, b)
            contrast = wcag_contrast(rgb, bg_rgb)

            palette.append({
                "role": role,
                "oklch": f"{L:.2f} {C:.3f} {H:.0f}",
                "hex": rgb_to_hex(r, g, b),
                "rgb": list(rgb),
                "contrast_on_bg": round(contrast, 1),
                "luminance": round(relative_luminance(r, g, b), 3),
            })

        palette.sort(key=lambda c: c["luminance"])
        return palette

    def _mock_palette(self) -> List[Dict[str, Any]]:
        return [
            {"role": "bg.base", "oklch": "0.18 0.01 260", "hex": "#141517", "rgb": [20, 21, 23], "contrast_on_bg": 1.0, "luminance": 0.006},
            {"role": "bg.subtle", "oklch": "0.22 0.01 260", "hex": "#1e2027", "rgb": [30, 32, 39], "contrast_on_bg": 1.2, "luminance": 0.015},
            {"role": "neutral", "oklch": "0.45 0.02 220", "hex": "#4a5568", "rgb": [74, 85, 104], "contrast_on_bg": 4.1, "luminance": 0.13},
            {"role": "accent.blue", "oklch": "0.55 0.22 262", "hex": "#2563eb", "rgb": [37, 99, 235], "contrast_on_bg": 5.2, "luminance": 0.17},
            {"role": "fg.muted", "oklch": "0.75 0.04 80", "hex": "#b8a890", "rgb": [184, 168, 144], "contrast_on_bg": 7.3, "luminance": 0.42},
            {"role": "fg.primary", "oklch": "0.96 0.01 90", "hex": "#f4f1ea", "rgb": [244, 241, 234], "contrast_on_bg": 14.2, "luminance": 0.91},
        ]
