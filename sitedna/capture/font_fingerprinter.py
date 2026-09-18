from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Tuple

FONT_DETECTION_SCRIPT = """
() => {
  const results = [];
  const selectors = ['h1', 'h2', 'h3', '.heading', '[class*="title"]', '.hero-text', 'body', 'p'];

  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (!el) continue;
    const s = window.getComputedStyle(el);

    results.push({
      selector: sel,
      fontFamily: s.fontFamily,
      fontStyle: s.fontStyle,
      fontWeight: s.fontWeight,
      fontSize: s.fontSize,
      letterSpacing: s.letterSpacing,
      lineHeight: s.lineHeight,
    });
  }

  // Check what font files are actually loaded
  const loadedFonts = [];
  for (const font of document.fonts) {
    if (font.status === 'loaded') {
      loadedFonts.push({ family: font.family, style: font.style, weight: font.weight });
    }
  }

  return { computed: results, loaded: loadedFonts };
}
"""

KNOWN_SERIF_FONTS = [
    ("EB Garamond", "serif"),
    ("Cormorant Garamond", "serif"),
    ("Playfair Display", "serif"),
    ("Lora", "serif"),
    ("Merriweather", "serif"),
    ("PT Serif", "serif"),
    ("Libre Baskerville", "serif"),
    ("Crimson Text", "serif"),
    ("Source Serif 4", "serif"),
    ("Spectral", "serif"),
]

KNOWN_SANS_FONTS = [
    ("Inter", "sans-serif"),
    ("DM Sans", "sans-serif"),
    ("Plus Jakarta Sans", "sans-serif"),
    ("Neue Montreal", "sans-serif"),
    ("General Sans", "sans-serif"),
    ("Satoshi", "sans-serif"),
    ("Manrope", "sans-serif"),
    ("Cabinet Grotesk", "sans-serif"),
    ("Space Grotesk", "sans-serif"),
]

KNOWN_MONO_FONTS = [
    ("JetBrains Mono", "monospace"),
    ("Fira Code", "monospace"),
    ("Space Mono", "monospace"),
    ("IBM Plex Mono", "monospace"),
]


class FontFingerprinter:
    def __init__(self, session: Any) -> None:
        self.session = session

    async def fingerprint(self) -> Dict[str, Any]:
        if not self.session.is_available():
            return self._mock_result()

        raw = await self.session.evaluate(FONT_DETECTION_SCRIPT)
        if not raw:
            return self._mock_result()

        computed = raw.get("computed", [])
        loaded = raw.get("loaded", [])

        display_font = self._identify_display_font(computed, loaded)
        body_font = self._identify_body_font(computed)

        return {
            "display": display_font,
            "body": body_font,
            "loaded_fonts": loaded,
            "raw_computed": computed,
        }

    def _identify_display_font(
        self, computed: List[Dict], loaded: List[Dict]
    ) -> Dict[str, Any]:
        loaded_families = {f["family"].strip('"').lower() for f in loaded}
        h1_entry = next((c for c in computed if c["selector"] in ("h1", ".heading")), None)
        if not h1_entry:
            h1_entry = computed[0] if computed else {}

        raw_family = h1_entry.get("fontFamily", "serif")
        primary = raw_family.split(",")[0].strip().strip('"').lower()

        is_serif = any(s in raw_family.lower() for s in ("serif", "garamond", "times", "georgia", "caslon"))
        is_sans = any(s in raw_family.lower() for s in ("sans", "inter", "helvetica", "arial", "grotesk"))

        catalog = KNOWN_SERIF_FONTS if is_serif else KNOWN_SANS_FONTS if is_sans else KNOWN_SERIF_FONTS

        matched_name, matched_cat = catalog[0]
        best_score = 0.0
        for font_name, category in catalog:
            score = self._similarity_score(primary, font_name.lower())
            if score > best_score:
                best_score = score
                matched_name = font_name
                matched_cat = category

        # Boost score if it's in loaded fonts
        if matched_name.lower() in loaded_families:
            best_score = min(1.0, best_score + 0.2)

        stack = [matched_name]
        if is_serif:
            stack.extend(["Georgia", "Times New Roman", "serif"])
        else:
            stack.extend(["Helvetica Neue", "Arial", "sans-serif"])

        return {
            "raw_family": raw_family,
            "matched": {"family": matched_name, "category": matched_cat, "score": round(best_score, 2), "method": "stack_heuristic"},
            "stack": stack,
            "is_serif": is_serif,
            "is_sans": is_sans,
            "weight": h1_entry.get("fontWeight", "400"),
            "size": h1_entry.get("fontSize", "96px"),
            "letter_spacing": h1_entry.get("letterSpacing", "-0.03em"),
        }

    def _identify_body_font(self, computed: List[Dict]) -> Dict[str, Any]:
        body_entry = next((c for c in computed if c["selector"] in ("body", "p")), None)
        if not body_entry:
            return {"raw_family": "sans-serif", "stack": ["Inter", "sans-serif"]}

        raw = body_entry.get("fontFamily", "sans-serif")
        return {
            "raw_family": raw,
            "stack": [raw.split(",")[0].strip().strip('"'), "sans-serif"],
            "size": body_entry.get("fontSize", "16px"),
        }

    def _similarity_score(self, a: str, b: str) -> float:
        a_words = set(a.lower().split())
        b_words = set(b.lower().split())
        if not a_words or not b_words:
            return 0.0
        intersection = a_words.intersection(b_words)
        union = a_words.union(b_words)
        return len(intersection) / len(union)

    def _mock_result(self) -> Dict[str, Any]:
        return {
            "display": {
                "raw_family": '"Apple Garamond", "EB Garamond", Georgia, serif',
                "matched": {"family": "EB Garamond", "category": "serif", "score": 0.94, "method": "stack_heuristic"},
                "stack": ["EB Garamond", "Georgia", "Times New Roman", "serif"],
                "is_serif": True,
                "is_sans": False,
                "weight": "400",
                "size": "clamp(3rem, 8vw, 7rem)",
                "letter_spacing": "-0.03em",
            },
            "body": {
                "raw_family": '"Inter", -apple-system, sans-serif',
                "stack": ["Inter", "sans-serif"],
                "size": "16px",
            },
            "loaded_fonts": [],
            "raw_computed": [],
        }
