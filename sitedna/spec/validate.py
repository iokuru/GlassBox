from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from sitedna.spec.schema import SiteDNA


@dataclass
class ValidationResult:
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    confidence: Dict[str, float] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.valid


def validate_sitedna(spec: SiteDNA) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []
    confidence: Dict[str, float] = {}

    if not spec.source.url:
        errors.append("source.url is required")

    if not spec.tokens.palette:
        warnings.append("No palette tokens extracted — color accuracy will be low")
        confidence["tokens"] = 0.2
    else:
        bg_roles = [c.role for c in spec.tokens.palette if "bg" in c.role]
        fg_roles = [c.role for c in spec.tokens.palette if "fg" in c.role]
        palette_score = min(1.0, len(spec.tokens.palette) / 6.0)
        if not bg_roles:
            warnings.append("No background color role found in palette")
            palette_score *= 0.7
        if not fg_roles:
            warnings.append("No foreground color role found in palette")
            palette_score *= 0.7
        confidence["tokens"] = round(palette_score, 2)

    if not spec.layout.sections:
        warnings.append("No layout sections detected")
        confidence["layout"] = 0.1
    else:
        confidence["layout"] = round(min(1.0, len(spec.layout.sections) / 4.0), 2)

    motion_signals = (
        len(spec.motion.entry)
        + len(spec.motion.scroll_linked)
        + len(spec.motion.mouse_parallax)
        + len(spec.motion.interactions)
    )
    if motion_signals == 0:
        warnings.append("No motion data captured — animated effects will not reproduce")
        confidence["motion"] = 0.0
    else:
        confidence["motion"] = round(min(1.0, motion_signals / 8.0), 2)

    font_resolved = bool(
        spec.tokens.type.display
        and spec.tokens.type.display.matched
        and spec.tokens.type.display.matched.get("score", 0) >= 0.7
    )
    if not font_resolved:
        warnings.append("Display font not matched with high confidence — substitute may differ visually")

    spec.provenance.confidence = confidence
    spec.provenance.warnings.extend(warnings)

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        confidence=confidence,
    )


def confidence_summary(result: ValidationResult) -> str:
    parts = []
    for domain, score in result.confidence.items():
        bar_filled = int(score * 10)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)
        parts.append(f"  {domain:10s} [{bar}] {score:.0%}")
    return "\n".join(parts)
