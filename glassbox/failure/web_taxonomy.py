from __future__ import annotations

from typing import Any, Dict, List, Optional


WEB_FAILURE_TYPES: Dict[str, Dict[str, Any]] = {
    "BOT_WALL": {
        "description": "Cloudflare, PerimeterX, or similar bot detection blocking capture",
        "severity": "high",
        "is_recoverable": True,
        "default_strategy": "retry_with_backoff",
        "browser_visible": True,
        "detection_signals": ["cf-ray header", "403 Forbidden", "captcha", "__cf_bm cookie"],
    },
    "MODAL_OCCLUSION": {
        "description": "Cookie consent or paywall modal covering content during capture",
        "severity": "medium",
        "is_recoverable": True,
        "default_strategy": "apply_patch",
        "browser_visible": True,
        "detection_signals": ["z-index > 9000", "position fixed", "aria-modal", "dialog role"],
    },
    "LAZY_CONTENT": {
        "description": "IntersectionObserver-gated content not rendered at capture time",
        "severity": "medium",
        "is_recoverable": True,
        "default_strategy": "replan",
        "browser_visible": False,
        "detection_signals": ["loading=lazy", "data-src", "IntersectionObserver", "placeholder skeleton"],
    },
    "WEBGL_BACKGROUND": {
        "description": "Three.js or WebGL canvas background that cannot be inspected via DOM",
        "severity": "medium",
        "is_recoverable": False,
        "default_strategy": "skip_and_log",
        "browser_visible": True,
        "detection_signals": ["canvas", "THREE.WebGLRenderer", "gl context"],
    },
    "LICENSED_FONT": {
        "description": "Commercial font (Neue Haas Grotesk, Söhne, etc.) not available via CDN",
        "severity": "low",
        "is_recoverable": True,
        "default_strategy": "apply_patch",
        "browser_visible": False,
        "detection_signals": ["fonts.adobe.com", "typography.com", "FOUT after load"],
    },
    "PHYSICS_ANIMATION": {
        "description": "Spring or inertia-based animation beyond linear regression recovery",
        "severity": "low",
        "is_recoverable": True,
        "default_strategy": "replan",
        "browser_visible": False,
        "detection_signals": ["getAnimations() returns empty", "canvas animation", "raf velocity"],
    },
    "CDP_DISCONNECT": {
        "description": "Chrome DevTools Protocol session lost — tab crash, timeout, or OOM",
        "severity": "high",
        "is_recoverable": True,
        "default_strategy": "retry_with_backoff",
        "browser_visible": False,
        "detection_signals": ["Target.detachedFromTarget", "WebSocket disconnect", "Session.disconnected"],
    },
    "VISUAL_REGRESSION": {
        "description": "Clone SSIM score below threshold — visual fidelity too low after repair",
        "severity": "medium",
        "is_recoverable": True,
        "default_strategy": "replan",
        "browser_visible": False,
        "detection_signals": ["ssim < 0.75", "lpips > 0.3", "palette delta_e > 15"],
    },
    "SCORE_PLATEAU": {
        "description": "Repair loop has stopped improving — max iterations reached with no gain",
        "severity": "low",
        "is_recoverable": False,
        "default_strategy": "skip_and_log",
        "browser_visible": False,
        "detection_signals": ["score_delta < 0.01 for 3+ iterations"],
    },
    "LOCALE_VARIANT": {
        "description": "Site serving different content based on geo-IP or accept-language header",
        "severity": "low",
        "is_recoverable": True,
        "default_strategy": "retry_with_backoff",
        "browser_visible": False,
        "detection_signals": ["hreflang", "content-language header", "302 redirect to locale"],
    },
}


class WebFailureClassifier:
    def classify_capture_error(
        self, error_message: str, status_code: Optional[int] = None
    ) -> Optional[str]:
        error_lower = error_message.lower()

        if status_code in (403, 429) or any(
            sig in error_lower for sig in ["cloudflare", "cf-ray", "captcha", "perimeter"]
        ):
            return "BOT_WALL"

        if any(
            sig in error_lower
            for sig in ["cdp", "websocket disconnect", "target closed", "session disconnected"]
        ):
            return "CDP_DISCONNECT"

        if any(sig in error_lower for sig in ["modal", "dialog", "cookie consent"]):
            return "MODAL_OCCLUSION"

        if any(sig in error_lower for sig in ["intersectionobserver", "lazy", "data-src"]):
            return "LAZY_CONTENT"

        if any(sig in error_lower for sig in ["webgl", "three.js", "canvas renderer"]):
            return "WEBGL_BACKGROUND"

        if "font" in error_lower and any(
            s in error_lower for s in ["adobe", "typography.com", "cloud.typography"]
        ):
            return "LICENSED_FONT"

        if any(sig in error_lower for sig in ["ssim", "lpips", "visual regression"]):
            return "VISUAL_REGRESSION"

        if "plateau" in error_lower or "no improvement" in error_lower:
            return "SCORE_PLATEAU"

        return None

    def get_recovery_hints(self, failure_type: str) -> List[str]:
        info = WEB_FAILURE_TYPES.get(failure_type, {})
        strategy = info.get("default_strategy", "skip_and_log")
        signals = info.get("detection_signals", [])

        hints = [f"Detected: {failure_type}"]
        if signals:
            hints.append(f"Signals: {', '.join(signals[:3])}")
        hints.append(f"Recovery strategy: {strategy}")
        return hints
