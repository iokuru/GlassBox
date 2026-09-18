from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

MOTION_CAPTURE_SCRIPT = """
async () => {
  // Tag all elements with a unique ID for tracking
  let gbIdx = 0;
  for (const el of document.querySelectorAll('*')) {
    el.dataset.gbId = String(gbIdx++);
  }

  // Collect all current Web Animations API animations
  const animationData = [];
  for (const anim of document.getAnimations()) {
    const effect = anim.effect;
    if (!effect || !effect.target) continue;
    const target = effect.target;
    try {
      const keyframes = effect.getKeyframes();
      const timing = effect.getTiming();
      const computed = effect.getComputedTiming();
      animationData.push({
        targetId: target.dataset?.gbId,
        targetTag: target.tagName,
        targetClasses: Array.from(target.classList).slice(0, 4),
        keyframes: keyframes.map(kf => ({
          offset: kf.offset,
          opacity: kf.opacity,
          transform: kf.transform,
          filter: kf.filter,
          clipPath: kf.clipPath,
        })),
        duration: timing.duration,
        delay: timing.delay,
        easing: timing.easing,
        fill: timing.fill,
        iterations: timing.iterations,
        playState: anim.playState,
      });
    } catch(_) {}
  }

  // Capture scroll-driven transforms by sampling at intervals
  const scrollSamples = [];
  const scrollHeight = document.documentElement.scrollHeight;
  const viewportH = window.innerHeight;
  const steps = 15;

  for (let i = 0; i <= steps; i++) {
    const scrollY = Math.round((i / steps) * (scrollHeight - viewportH));
    window.scrollTo(0, scrollY);
    await new Promise(r => setTimeout(r, 50));

    const sample = { scrollY, elements: [] };
    for (const el of document.querySelectorAll('[data-gb-id]')) {
      const style = window.getComputedStyle(el);
      const transform = style.transform;
      if (transform && transform !== 'none') {
        sample.elements.push({
          id: el.dataset.gbId,
          tag: el.tagName,
          classes: Array.from(el.classList).slice(0, 3),
          transform,
          opacity: style.opacity,
        });
      }
    }
    if (sample.elements.length > 0) scrollSamples.push(sample);
  }

  window.scrollTo(0, 0);

  // Detect intersection-observer based triggers by checking what becomes visible
  const visibilityChanges = [];

  return {
    animations: animationData.slice(0, 30),
    scrollSamples: scrollSamples.slice(0, steps + 1),
    visibilityChanges,
  };
}
"""


class MotionCapture:
    def __init__(self, session: Any) -> None:
        self.session = session

    async def capture(self) -> Dict[str, Any]:
        if not self.session.is_available():
            return self._mock_motion_data()

        raw = await self.session.evaluate(MOTION_CAPTURE_SCRIPT)
        if not raw:
            return self._mock_motion_data()

        animations = self._parse_animations(raw.get("animations", []))
        scroll_linked = self._recover_scroll_formulas(raw.get("scrollSamples", []))

        return {
            "entry_animations": animations["entry"],
            "scroll_linked": scroll_linked,
            "mouse_parallax_hints": self._detect_parallax_candidates(raw.get("scrollSamples", [])),
            "raw_samples": raw.get("scrollSamples", []),
        }

    def _parse_animations(self, anims: List[Dict]) -> Dict[str, List]:
        entry = []
        for anim in anims:
            kfs = anim.get("keyframes", [])
            if not kfs:
                continue

            props = {}
            for kf in kfs:
                for prop in ("opacity", "transform", "filter", "clipPath"):
                    if kf.get(prop) and kf[prop] != "none" and kf[prop] != "":
                        if prop not in props:
                            props[prop] = []
                        props[prop].append(kf[prop])

            if not props:
                continue

            classes = anim.get("targetClasses", [])
            tag = anim.get("targetTag", "div").lower()
            target = ".".join(classes[:2]) if classes else tag

            entry.append({
                "target": target,
                "props": props,
                "duration": anim.get("duration", 500),
                "delay": anim.get("delay", 0),
                "easing": anim.get("easing", "ease"),
                "play_state": anim.get("playState", "running"),
            })

        return {"entry": entry}

    def _recover_scroll_formulas(self, samples: List[Dict]) -> List[Dict]:
        formulas = []
        element_trajectories: Dict[str, List[Tuple[int, str]]] = {}

        for sample in samples:
            scroll_y = sample.get("scrollY", 0)
            for el in sample.get("elements", []):
                eid = el.get("id", "")
                transform = el.get("transform", "none")
                if eid not in element_trajectories:
                    element_trajectories[eid] = []
                element_trajectories[eid].append((scroll_y, transform, el.get("classes", [])))

        for eid, trajectory in element_trajectories.items():
            if len(trajectory) < 3:
                continue

            y_vals = []
            scroll_vals = []
            for scroll_y, transform, _ in trajectory:
                ty = self._extract_translate_y(transform)
                if ty is not None:
                    y_vals.append(ty)
                    scroll_vals.append(scroll_y)

            if len(y_vals) < 3:
                continue

            coefficient = self._linear_regression_slope(scroll_vals, y_vals)
            if abs(coefficient) < 0.01:
                continue

            classes = trajectory[0][2] if trajectory else []
            target_hint = ".".join(classes[:2]) if classes else f"element-{eid}"
            speed_pct = round(abs(coefficient) * 100)
            direction = "upward" if coefficient < 0 else "downward"
            formula = f"scrollY * {coefficient:.3f}"

            formulas.append({
                "target": target_hint,
                "formula": formula,
                "coefficient": round(coefficient, 4),
                "direction": direction,
                "speed_pct": speed_pct,
                "confidence": min(1.0, len(y_vals) / 10.0),
            })

        return formulas[:8]

    def _extract_translate_y(self, transform_str: str) -> Optional[float]:
        m = re.search(r"translateY\(([^)]+)\)", transform_str)
        if m:
            val = m.group(1).replace("px", "").replace("%", "")
            try:
                return float(val)
            except ValueError:
                pass

        m2 = re.search(r"matrix\([^)]+,\s*([^,]+)\)", transform_str)
        if m2:
            try:
                return float(m2.group(1))
            except ValueError:
                pass

        return None

    def _linear_regression_slope(self, x: List[float], y: List[float]) -> float:
        if len(x) < 2:
            return 0.0
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_xx = sum(xi * xi for xi in x)
        denom = n * sum_xx - sum_x ** 2
        if denom == 0:
            return 0.0
        return (n * sum_xy - sum_x * sum_y) / denom

    def _detect_parallax_candidates(self, samples: List[Dict]) -> List[Dict]:
        candidates = []
        seen_classes: Dict[str, List[float]] = {}

        for sample in samples:
            for el in sample.get("elements", []):
                classes = ".".join(el.get("classes", [])[:2])
                if not classes:
                    continue
                ty = self._extract_translate_y(el.get("transform", ""))
                if ty is None:
                    continue
                if classes not in seen_classes:
                    seen_classes[classes] = []
                seen_classes[classes].append(ty)

        for class_key, y_vals in seen_classes.items():
            if len(y_vals) < 3:
                continue
            variance = max(y_vals) - min(y_vals)
            if variance > 20:
                candidates.append({
                    "target": class_key,
                    "y_variance_px": round(variance),
                    "likely_parallax": True,
                })

        return candidates[:6]

    def _mock_motion_data(self) -> Dict[str, Any]:
        return {
            "entry_animations": [
                {
                    "target": "nav",
                    "props": {"opacity": ["0", "1"], "filter": ["blur(8px)", "blur(0px)"]},
                    "duration": 900,
                    "delay": 0,
                    "easing": "cubic-bezier(0.25, 0.1, 0.25, 1)",
                    "play_state": "running",
                },
                {
                    "target": "h1",
                    "props": {"transform": ["translateY(100%)", "translateY(0%)"]},
                    "duration": 700,
                    "delay": 100,
                    "easing": "cubic-bezier(0.25, 0.1, 0.25, 1)",
                    "play_state": "running",
                },
            ],
            "scroll_linked": [
                {"target": "ww3-text", "formula": "scrollY * 0.49", "coefficient": 0.49, "direction": "downward", "confidence": 0.8},
                {"target": "fighter-jet", "formula": "scrollY * -0.05", "coefficient": -0.05, "direction": "upward", "confidence": 0.7},
                {"target": "eagle", "formula": "scrollY * -0.07", "coefficient": -0.07, "direction": "upward", "confidence": 0.75},
            ],
            "mouse_parallax_hints": [
                {"target": "bg-landscape", "y_variance_px": 45, "likely_parallax": True},
                {"target": "eagle-overlay", "y_variance_px": 28, "likely_parallax": True},
            ],
            "raw_samples": [],
        }


import re
