from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from sitedna.capture.cdp_session import CDPSession, MockCDPSession
from sitedna.capture.asset_harvester import AssetHarvester
from sitedna.capture.dom_extractor import DOMExtractor
from sitedna.capture.font_fingerprinter import FontFingerprinter
from sitedna.capture.motion_capture import MotionCapture
from sitedna.capture.palette import PaletteExtractor
from sitedna.capture.style_extractor import StyleExtractor
from sitedna.spec.schema import (
    AssetRecord,
    ColorToken,
    CaptureSource,
    DesignTokens,
    EntryAnimation,
    LayoutSpec,
    MotionSpec,
    MouseParallaxLayer,
    ProvenanceRecord,
    ScrollAnimation,
    SectionLayout,
    SiteDNA,
    TypeFace,
    TypeStep,
    TypeTokens,
)
from sitedna.spec.validate import validate_sitedna, confidence_summary


class CaptureProgress:
    def __init__(self) -> None:
        self.stages: Dict[str, str] = {}

    def update(self, stage: str, status: str = "done") -> None:
        self.stages[stage] = status
        symbol = "+" if status == "done" else "~" if status == "running" else "!"
        print(f"  [{symbol}] {stage}")


class CapturePipeline:
    def __init__(self, url: str, viewport: tuple = (1440, 900), use_mock: bool = False) -> None:
        self.url = url
        self.viewport = viewport
        self.use_mock = use_mock

    async def capture(self) -> SiteDNA:
        progress = CaptureProgress()
        start_time = time.time()
        print(f"\nCapturing SiteDNA from: {self.url}")
        print(f"Viewport: {self.viewport[0]}×{self.viewport[1]}")
        print()

        SessionClass = MockCDPSession if self.use_mock else CDPSession

        async with SessionClass(self.url, self.viewport) as session:
            # Stage 1: DOM
            progress.update("DOM extraction", "running")
            dom_extractor = DOMExtractor(session)
            dom_data = await dom_extractor.extract()
            progress.update("DOM extraction")

            # Stage 2: Styles
            progress.update("Style extraction", "running")
            style_extractor = StyleExtractor(session)
            style_data = await style_extractor.extract()
            progress.update("Style extraction")

            # Stage 3: Fonts
            progress.update("Font fingerprinting", "running")
            font_fp = FontFingerprinter(session)
            font_data = await font_fp.fingerprint()
            progress.update("Font fingerprinting")

            # Stage 4: Palette
            progress.update("Palette extraction", "running")
            palette_extractor = PaletteExtractor(session)
            palette_data = await palette_extractor.extract(style_data.get("raw_colors"))
            progress.update("Palette extraction")

            # Stage 5: Motion
            progress.update("Motion capture", "running")
            motion_capture = MotionCapture(session)
            motion_data = await motion_capture.capture()
            progress.update("Motion capture")

            # Stage 6: Assets
            progress.update("Asset harvesting", "running")
            asset_harvester = AssetHarvester(session)
            asset_data = await asset_harvester.harvest()
            progress.update("Asset harvesting")

        capture_duration_ms = (time.time() - start_time) * 1000.0
        progress.update("Assembling SiteDNA spec", "running")
        spec = self._assemble_spec(
            url=self.url,
            viewport=self.viewport,
            capture_duration_ms=capture_duration_ms,
            dom=dom_data,
            styles=style_data,
            fonts=font_data,
            palette=palette_data,
            motion=motion_data,
            assets=asset_data,
        )
        progress.update("Assembling SiteDNA spec")

        result = validate_sitedna(spec)
        print(f"\nConfidence Scores:\n{confidence_summary(result)}")
        if result.warnings:
            print(f"\nWarnings:")
            for w in result.warnings:
                print(f"  • {w}")

        return spec

    def _assemble_spec(
        self,
        url: str,
        viewport: tuple,
        capture_duration_ms: float,
        dom: Dict,
        styles: Dict,
        fonts: Dict,
        palette: Dict,
        motion: Dict,
        assets: list,
    ) -> SiteDNA:
        # Tokens
        color_tokens = [
            ColorToken(
                role=c["role"],
                oklch=c["oklch"],
                hex=c["hex"],
                coverage=c.get("coverage", 0.0),
                contrast_on_bg=c.get("contrast_on_bg"),
            )
            for c in palette
        ]

        display_font = fonts.get("display", {})
        matched = display_font.get("matched", {})
        display_typef = TypeFace(
            stack=display_font.get("stack", ["serif"]),
            matched={
                "family": matched.get("family", "EB Garamond"),
                "score": matched.get("score", 0.7),
                "method": matched.get("method", "stack_heuristic"),
            },
            scale=[
                TypeStep(
                    step="h1",
                    size=display_font.get("size", "clamp(3rem,8vw,7rem)"),
                    tracking=display_font.get("letter_spacing", "-0.03em"),
                    leading=0.95,
                    weight=display_font.get("weight", "400"),
                )
            ],
        )
        body_font = fonts.get("body", {})
        body_typef = TypeFace(
            stack=body_font.get("stack", ["sans-serif"]),
            scale=[TypeStep(step="body", size=body_font.get("size", "16px"))],
        )

        tokens = DesignTokens(
            palette=color_tokens,
            type=TypeTokens(display=display_typef, body=body_typef),
            spacing={
                "base": 4,
                "rhythm": styles.get("spacings", [8, 16, 24, 40, 64, 96]),
            },
            radii=styles.get("border_radii", [0, 6, 9]),
        )

        # Layout
        sections = []
        for sec in dom.get("sections", []):
            sections.append(
                SectionLayout(
                    id=sec.get("id", "section"),
                    height=f"{sec.get('height_vh', 60)}vh",
                    positioning={
                        "type": sec.get("type", "content"),
                        "position": sec.get("position", "static"),
                    },
                    sticky={"position": "sticky", "top": sec.get("top", "0")} if sec.get("sticky") else None,
                )
            )
        layout = LayoutSpec(
            sections=sections,
            breakpoints={str(bp): bp for bp in styles.get("breakpoints", [768])},
        )

        # Motion
        entry_anims = []
        for a in motion.get("entry_animations", []):
            entry_anims.append(
                EntryAnimation(
                    target=a.get("target", "element"),
                    props=a.get("props", {}),
                    duration=float(a.get("duration", 500)) / 1000.0,
                    delay=float(a.get("delay", 0)) / 1000.0,
                    easing=[0.25, 0.1, 0.25, 1],
                )
            )

        scroll_anims = []
        for s in motion.get("scroll_linked", []):
            scroll_anims.append(
                ScrollAnimation(
                    target=s.get("target", "element"),
                    trigger="scroll",
                    formula=s.get("formula"),
                )
            )

        parallax_layers = []
        for h in motion.get("mouse_parallax_hints", []):
            parallax_layers.append(
                MouseParallaxLayer(
                    target=h.get("target", "element"),
                    strength=min(20.0, h.get("y_variance_px", 15) * 0.3),
                    invert=False,
                    ease=0.08,
                )
            )

        motion_spec = MotionSpec(
            entry=entry_anims,
            scroll_linked=scroll_anims,
            mouse_parallax=parallax_layers,
        )

        # Assets
        asset_records = []
        for a in assets:
            asset_records.append(
                AssetRecord(
                    id=a.get("id", "asset"),
                    kind=a.get("category", "asset"),
                    alpha=a.get("needs_alpha_matting", False),
                    url=a.get("src"),
                    generation_prompt=a.get("generation_prompt"),
                    dimensions=(a.get("width", 0), a.get("height", 0)),
                )
            )

        return SiteDNA(
            sitedna="0.1",
            source=CaptureSource(
                url=url,
                captured_at=datetime.now(timezone.utc).isoformat(),
                viewport=viewport,
                capture_duration_ms=round(capture_duration_ms, 1),
            ),
            tokens=tokens,
            layout=layout,
            motion=motion_spec,
            assets=asset_records,
            provenance=ProvenanceRecord(
                captured_by="sitedna/0.1",
            ),
        )

    def save(self, spec: SiteDNA, output_path: str) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(json.loads(spec.model_dump_json()), f, indent=2)
        print(f"\nSiteDNA saved to: {path}")


def capture_sync(url: str, output: Optional[str] = None, use_mock: bool = False) -> SiteDNA:
    pipeline = CapturePipeline(url=url, use_mock=use_mock)
    spec = asyncio.run(pipeline.capture())
    if output:
        pipeline.save(spec, output)
    return spec
