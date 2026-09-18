from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

STYLE_EXTRACTION_SCRIPT = """
() => {
  const tokens = {
    colors: new Set(),
    fontFamilies: new Set(),
    fontSizes: [],
    fontWeights: new Set(),
    letterSpacings: new Set(),
    lineHeights: new Set(),
    borderRadii: new Set(),
    spacings: new Set(),
    cssVars: {},
    breakpoints: [],
  };

  // Extract CSS custom properties from :root
  for (const sheet of document.styleSheets) {
    try {
      for (const rule of sheet.cssRules) {
        if (rule.selectorText === ':root' || rule.selectorText === 'html') {
          const style = rule.style;
          for (let i = 0; i < style.length; i++) {
            const prop = style[i];
            if (prop.startsWith('--')) {
              tokens.cssVars[prop] = style.getPropertyValue(prop).trim();
            }
          }
        }
        if (rule instanceof CSSMediaRule) {
          const conditionText = rule.conditionText || rule.media?.mediaText;
          const match = conditionText?.match(/min-width:\\s*(\\d+)px/);
          if (match) tokens.breakpoints.push(parseInt(match[1]));
        }
      }
    } catch (_) {}
  }

  // Sample computed styles from representative elements
  const selectors = [
    'h1', 'h2', 'h3', 'h4', 'p', 'a', 'button', 'nav',
    '[class*="hero"]', '[class*="heading"]', '[class*="cta"]',
  ];
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (!el) continue;
    const s = window.getComputedStyle(el);
    if (s.color) tokens.colors.add(s.color);
    if (s.backgroundColor && s.backgroundColor !== 'rgba(0, 0, 0, 0)') tokens.colors.add(s.backgroundColor);
    if (s.fontFamily) tokens.fontFamilies.add(s.fontFamily);
    if (s.fontSize) tokens.fontSizes.push({ selector: sel, value: s.fontSize });
    if (s.fontWeight) tokens.fontWeights.add(s.fontWeight);
    if (s.letterSpacing && s.letterSpacing !== 'normal') tokens.letterSpacings.add(s.letterSpacing);
    if (s.lineHeight && s.lineHeight !== 'normal') tokens.lineHeights.add(s.lineHeight);
    if (s.borderRadius && s.borderRadius !== '0px') tokens.borderRadii.add(s.borderRadius);
  }

  // Sample spacing from sections
  for (const el of document.querySelectorAll('section, main, header, footer')) {
    const s = window.getComputedStyle(el);
    ['paddingTop', 'paddingBottom', 'marginTop', 'marginBottom'].forEach(p => {
      const v = s[p];
      if (v && v !== '0px') tokens.spacings.add(v);
    });
  }

  return {
    colors: Array.from(tokens.colors),
    fontFamilies: Array.from(tokens.fontFamilies),
    fontSizes: tokens.fontSizes.slice(0, 12),
    fontWeights: Array.from(tokens.fontWeights),
    letterSpacings: Array.from(tokens.letterSpacings),
    lineHeights: Array.from(tokens.lineHeights),
    borderRadii: Array.from(tokens.borderRadii),
    spacings: Array.from(tokens.spacings).slice(0, 20),
    cssVars: tokens.cssVars,
    breakpoints: [...new Set(tokens.breakpoints)].sort((a,b) => a-b),
  };
}
"""


class StyleExtractor:
    def __init__(self, session: Any) -> None:
        self.session = session

    async def extract(self) -> Dict[str, Any]:
        if not self.session.is_available():
            return self._mock_styles()

        raw = await self.session.evaluate(STYLE_EXTRACTION_SCRIPT)
        if not raw:
            return self._mock_styles()

        return {
            "raw_colors": raw.get("colors", []),
            "font_families": self._parse_font_stacks(raw.get("fontFamilies", [])),
            "font_sizes": raw.get("fontSizes", []),
            "font_weights": raw.get("fontWeights", []),
            "letter_spacings": raw.get("letterSpacings", []),
            "line_heights": raw.get("lineHeights", []),
            "border_radii": self._parse_px_values(raw.get("borderRadii", [])),
            "spacings": self._parse_px_values(raw.get("spacings", [])),
            "css_vars": raw.get("cssVars", {}),
            "breakpoints": raw.get("breakpoints", [768, 1024, 1440]),
        }

    def _parse_font_stacks(self, raw_families: List[str]) -> List[List[str]]:
        stacks = []
        seen = set()
        for family_str in raw_families:
            stack = [f.strip().strip('"\'') for f in family_str.split(",")]
            key = stack[0].lower() if stack else ""
            if key and key not in seen:
                seen.add(key)
                stacks.append(stack)
        return stacks

    def _parse_px_values(self, values: List[str]) -> List[int]:
        result = []
        for v in values:
            try:
                px = int(float(re.sub(r"[^\d.]", "", v)))
                if px > 0 and px not in result:
                    result.append(px)
            except (ValueError, TypeError):
                pass
        return sorted(result)

    def _mock_styles(self) -> Dict[str, Any]:
        return {
            "raw_colors": ["rgb(20, 21, 23)", "rgb(244, 241, 234)", "rgb(37, 99, 235)"],
            "font_families": [["Apple Garamond", "EB Garamond", "Georgia", "serif"]],
            "font_sizes": [
                {"selector": "h1", "value": "96px"},
                {"selector": "p", "value": "16px"},
            ],
            "font_weights": ["400", "600", "700"],
            "letter_spacings": ["-0.03em", "0.05em"],
            "line_heights": ["0.95", "1.5"],
            "border_radii": [6, 9],
            "spacings": [8, 16, 24, 40, 64, 96],
            "css_vars": {"--color-bg": "#141517", "--color-fg": "#f4f1ea"},
            "breakpoints": [768, 1440],
        }
