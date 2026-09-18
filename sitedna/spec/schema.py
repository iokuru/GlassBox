from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class ColorToken(BaseModel):
    role: str
    oklch: str
    hex: str
    coverage: float = 0.0
    contrast_on_bg: Optional[float] = None


class TypeStep(BaseModel):
    step: str
    size: str
    tracking: Optional[str] = None
    leading: Optional[float] = None
    weight: Optional[str] = None


class TypeFace(BaseModel):
    stack: List[str]
    matched: Optional[Dict[str, Any]] = None
    scale: List[TypeStep] = Field(default_factory=list)


class TypeTokens(BaseModel):
    display: Optional[TypeFace] = None
    body: Optional[TypeFace] = None
    mono: Optional[TypeFace] = None


class EasingTokens(BaseModel):
    standard: List[float] = Field(default_factory=lambda: [0.25, 0.1, 0.25, 1])
    expressive: List[float] = Field(default_factory=lambda: [0.22, 1, 0.36, 1])
    exit: List[float] = Field(default_factory=lambda: [0.4, 0, 1, 1])


class DesignTokens(BaseModel):
    palette: List[ColorToken] = Field(default_factory=list)
    type: TypeTokens = Field(default_factory=TypeTokens)
    spacing: Dict[str, Any] = Field(default_factory=dict)
    radii: List[int] = Field(default_factory=list)
    easing: EasingTokens = Field(default_factory=EasingTokens)


class SectionLayout(BaseModel):
    id: str
    height: Optional[str] = None
    positioning: Dict[str, Any] = Field(default_factory=dict)
    sticky: Optional[Dict[str, Any]] = None
    overlap_with: Optional[str] = None
    margin_top: Optional[str] = None


class LayoutSpec(BaseModel):
    sections: List[SectionLayout] = Field(default_factory=list)
    breakpoints: Dict[str, int] = Field(default_factory=dict)
    overlap_technique: Optional[str] = None


class EntryAnimation(BaseModel):
    target: str
    props: Dict[str, Any]
    technique: Optional[str] = None
    duration: float = 0.5
    stagger: float = 0.0
    delay: float = 0.0
    easing: List[float] = Field(default_factory=lambda: [0.25, 0.1, 0.25, 1])


class ScrollAnimation(BaseModel):
    target: str
    trigger: str
    range: Optional[List[str]] = None
    props: Optional[Dict[str, Any]] = None
    formula: Optional[str] = None


class MouseParallaxLayer(BaseModel):
    target: str
    strength: float = 15.0
    invert: bool = False
    ease: float = 0.08
    method: str = "lerp_dom_transform"


class Interaction(BaseModel):
    model_config = {"populate_by_name": True}

    target: str
    trigger: str
    from_value: str = Field(alias="from")
    to_value: str = Field(alias="to")
    property: str = "clip-path"
    duration: int = 300
    ease: str = "ease-out"


class MotionSpec(BaseModel):
    entry: List[EntryAnimation] = Field(default_factory=list)
    scroll_linked: List[ScrollAnimation] = Field(default_factory=list)
    mouse_parallax: List[MouseParallaxLayer] = Field(default_factory=list)
    interactions: List[Dict[str, Any]] = Field(default_factory=list)


class AssetRecord(BaseModel):
    id: str
    kind: str
    alpha: bool = False
    source_crop: Optional[List[int]] = None
    reconstructed_by: Optional[str] = None
    parent_plate: Optional[str] = None
    generation_prompt: Optional[str] = None
    local_path: Optional[str] = None
    url: Optional[str] = None
    dimensions: Optional[Tuple[int, int]] = None


class CaptureSource(BaseModel):
    url: str
    captured_at: str
    viewport: Tuple[int, int] = (1440, 900)
    capture_duration_ms: float = 0.0
    user_agent: Optional[str] = None


class ProvenanceRecord(BaseModel):
    captured_by: str = "sitedna/0.1"
    confidence: Dict[str, float] = Field(default_factory=dict)
    unresolved: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class SiteDNA(BaseModel):
    sitedna: str = "0.1"
    source: CaptureSource
    tokens: DesignTokens = Field(default_factory=DesignTokens)
    layout: LayoutSpec = Field(default_factory=LayoutSpec)
    motion: MotionSpec = Field(default_factory=MotionSpec)
    assets: List[AssetRecord] = Field(default_factory=list)
    provenance: ProvenanceRecord = Field(default_factory=ProvenanceRecord)
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)
