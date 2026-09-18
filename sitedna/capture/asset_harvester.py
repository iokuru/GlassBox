from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

ASSET_HARVEST_SCRIPT = """
() => {
  const assets = [];

  // img tags with srcset
  for (const img of document.querySelectorAll('img')) {
    const rect = img.getBoundingClientRect();
    if (rect.width < 30 || rect.height < 30) continue;
    assets.push({
      kind: 'img',
      src: img.src,
      srcset: img.srcset || null,
      alt: img.alt,
      width: Math.round(rect.width),
      height: Math.round(rect.height),
      rect: { x: Math.round(rect.x + scrollX), y: Math.round(rect.y + scrollY) },
      natural: { w: img.naturalWidth, h: img.naturalHeight },
    });
  }

  // CSS background images
  for (const el of document.querySelectorAll('*')) {
    const style = window.getComputedStyle(el);
    const bg = style.backgroundImage;
    if (!bg || bg === 'none') continue;
    const urlMatch = bg.match(/url\\(["']?([^"')]+)["']?\\)/);
    if (!urlMatch) continue;
    const rect = el.getBoundingClientRect();
    if (rect.width < 100 || rect.height < 100) continue;
    assets.push({
      kind: 'css-bg',
      src: urlMatch[1],
      width: Math.round(rect.width),
      height: Math.round(rect.height),
      rect: { x: Math.round(rect.x + scrollX), y: Math.round(rect.y + scrollY) },
      bgSize: style.backgroundSize,
      bgPosition: style.backgroundPosition,
    });
  }

  // Inline SVGs
  for (const svg of document.querySelectorAll('svg')) {
    const rect = svg.getBoundingClientRect();
    if (rect.width < 20) continue;
    const svgContent = svg.outerHTML.slice(0, 500);
    assets.push({
      kind: 'inline-svg',
      content_preview: svgContent,
      width: Math.round(rect.width),
      height: Math.round(rect.height),
    });
  }

  // Video backgrounds
  for (const video of document.querySelectorAll('video')) {
    const rect = video.getBoundingClientRect();
    if (rect.width < 100) continue;
    assets.push({
      kind: 'video',
      src: video.src || video.querySelector('source')?.src,
      poster: video.poster,
      width: Math.round(rect.width),
      height: Math.round(rect.height),
      autoplay: video.autoplay,
      muted: video.muted,
      loop: video.loop,
    });
  }

  return assets.slice(0, 30);
}
"""


def categorize_asset(asset: Dict[str, Any]) -> str:
    kind = asset.get("kind", "img")
    w = asset.get("width", 0)
    h = asset.get("height", 0)
    y_pos = asset.get("rect", {}).get("y", 0)

    if kind == "video":
        return "video-background"
    if kind == "inline-svg":
        return "decorative-svg"
    if kind == "css-bg" and w > 800 and h > 400:
        return "section-background"
    if y_pos < 200 and w > 600:
        return "hero-background"
    if h > 300 and w > 300:
        return "overlay"
    return "asset"


class AssetHarvester:
    def __init__(self, session: Any) -> None:
        self.session = session

    async def harvest(self) -> List[Dict[str, Any]]:
        if not self.session.is_available():
            return self._mock_assets()

        raw = await self.session.evaluate(ASSET_HARVEST_SCRIPT)
        if not raw:
            return self._mock_assets()

        processed = []
        for asset in raw:
            asset["category"] = categorize_asset(asset)
            asset["id"] = self._generate_id(asset)
            asset["needs_alpha_matting"] = asset.get("kind") == "img" and asset.get("height", 0) > 200
            processed.append(asset)

        return processed

    def _generate_id(self, asset: Dict[str, Any]) -> str:
        category = asset.get("category", "asset")
        src = asset.get("src", "")
        if src:
            name = src.split("/")[-1].split("?")[0].split(".")[0]
            return f"{category}-{name[:20]}"
        return f"{category}-{asset.get('kind', 'unknown')}"

    def _mock_assets(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "hero-background-landscape",
                "kind": "css-bg",
                "category": "section-background",
                "src": "/assets/landscape.jpg",
                "width": 1440,
                "height": 900,
                "rect": {"x": 0, "y": 0},
                "bgSize": "cover",
                "bgPosition": "center",
                "needs_alpha_matting": False,
                "generation_prompt": "Cinematic wartime landscape with muted tones, mountains, and golden haze",
            },
            {
                "id": "overlay-eagle",
                "kind": "img",
                "category": "overlay",
                "src": "/assets/eagle.png",
                "width": 320,
                "height": 260,
                "rect": {"x": 1100, "y": 600},
                "alpha": True,
                "needs_alpha_matting": True,
                "generation_prompt": "Eagle in flight, three-quarter view, muted cinematic grade, transparent background",
            },
            {
                "id": "overlay-fighter-jet",
                "kind": "img",
                "category": "overlay",
                "src": "/assets/fighter-jet.png",
                "width": 440,
                "height": 280,
                "rect": {"x": 0, "y": 500},
                "alpha": True,
                "needs_alpha_matting": True,
                "generation_prompt": "Fighter jet in flight, side view, wartime aesthetic, transparent background",
            },
            {
                "id": "decorative-svg",
                "kind": "inline-svg",
                "category": "decorative-svg",
                "content_preview": "<svg viewBox='0 0 24 24'...",
                "width": 48,
                "height": 48,
                "needs_alpha_matting": False,
            },
        ]
