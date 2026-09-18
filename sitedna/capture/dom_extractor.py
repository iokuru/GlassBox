from __future__ import annotations

from typing import Any, Dict, List, Optional
from sitedna.capture.cdp_session import CDPSession, MockCDPSession


DOM_EXTRACTION_SCRIPT = """
() => {
  const walk = (el, depth) => {
    if (!el || depth > 8) return null;
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    const tag = el.tagName?.toLowerCase() || '#text';

    // Skip invisible and tiny elements
    if (parseFloat(style.opacity) < 0.01) return null;
    if (rect.width < 2 && rect.height < 2 && el.children.length === 0) return null;

    const node = {
      tag,
      id: el.id || null,
      classes: Array.from(el.classList).slice(0, 8),
      rect: { x: Math.round(rect.x), y: Math.round(rect.y),
              w: Math.round(rect.width), h: Math.round(rect.height) },
      zIndex: style.zIndex,
      position: style.position,
      display: style.display,
      overflow: style.overflow,
      text: (el.children.length === 0 && tag !== 'img') ? el.textContent?.trim().slice(0, 80) : null,
      role: el.getAttribute('role') || null,
      children: [],
    };

    if (['header', 'nav', 'main', 'section', 'footer', 'article', 'aside'].includes(tag)) {
      node.semantic = true;
    }

    for (const child of el.children) {
      const c = walk(child, depth + 1);
      if (c) node.children.push(c);
    }
    return node;
  };

  const sections = [];
  const candidates = document.querySelectorAll('section, main > *, header, footer, [data-section], [id]');
  const seen = new Set();

  for (const el of candidates) {
    if (seen.has(el)) continue;
    seen.add(el);
    const rect = el.getBoundingClientRect();
    if (rect.height < 100) continue;
    const style = window.getComputedStyle(el);
    sections.push({
      id: el.id || el.getAttribute('data-section') || el.tagName.toLowerCase(),
      tag: el.tagName.toLowerCase(),
      rect: { x: Math.round(rect.x + window.scrollX), y: Math.round(rect.y + window.scrollY),
               w: Math.round(rect.width), h: Math.round(rect.height) },
      height_vh: Math.round((rect.height / window.innerHeight) * 100),
      position: style.position,
      top: style.top,
      zIndex: style.zIndex,
      overflow: style.overflow,
    });
  }

  return {
    title: document.title,
    url: location.href,
    viewport: { w: window.innerWidth, h: window.innerHeight },
    scrollHeight: document.documentElement.scrollHeight,
    sections,
    tree: walk(document.body, 0),
  };
}
"""


class DOMExtractor:
    def __init__(self, session: Any) -> None:
        self.session = session

    async def extract(self) -> Dict[str, Any]:
        if not self.session.is_available():
            return self._mock_dom()

        raw = await self.session.evaluate(DOM_EXTRACTION_SCRIPT)
        if not raw:
            return self._mock_dom()

        sections = self._classify_sections(raw.get("sections", []))
        return {
            "title": raw.get("title", ""),
            "url": raw.get("url", ""),
            "viewport": raw.get("viewport", {}),
            "scroll_height": raw.get("scrollHeight", 0),
            "sections": sections,
            "tree": raw.get("tree"),
        }

    def _classify_sections(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for i, sec in enumerate(sections):
            sec["index"] = i
            h = sec.get("height_vh", 0)
            if h >= 80:
                sec["type"] = "hero"
            elif h >= 40:
                sec["type"] = "content"
            else:
                sec["type"] = "panel"

            if sec.get("position") == "sticky":
                sec["sticky"] = True
        return sections

    def _mock_dom(self) -> Dict[str, Any]:
        return {
            "title": "Mock Page",
            "url": "https://example.com",
            "viewport": {"w": 1440, "h": 900},
            "scroll_height": 3000,
            "sections": [
                {"id": "hero", "tag": "section", "height_vh": 98, "type": "hero",
                 "position": "static", "rect": {"x": 0, "y": 0, "w": 1440, "h": 900}},
                {"id": "content", "tag": "section", "height_vh": 60, "type": "content",
                 "position": "static", "rect": {"x": 0, "y": 900, "w": 1440, "h": 540}},
            ],
            "tree": None,
        }
