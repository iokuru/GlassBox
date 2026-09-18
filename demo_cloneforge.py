"""
CloneForge end-to-end demo — runs capture + clone + mini bench with mock data.

Usage:
    python demo_cloneforge.py

No browser needed — uses MockCDPSession throughout.
"""

import asyncio
import json
import time

from sitedna.capture.pipeline import CapturePipeline
from sitedna.codegen.scaffold import ScaffoldGenerator
from sitedna.spec.validate import validate_sitedna, confidence_summary
from sitedna.verify.repair_loop import CloseLoopVerifier
import numpy as np


def hr(char="=", width=55):
    print(char * width)


def main():
    hr()
    print("  CLONEFORGE DEMO — GlassBox x SiteDNA")
    hr()
    print()

    target_url = "https://structured.money/"
    print(f"Target: {target_url}")
    print()

    # Phase 1: Capture
    print("Phase 1: SiteDNA Capture")
    hr("-")
    pipeline = CapturePipeline(url=target_url, use_mock=True)
    spec = asyncio.run(pipeline.capture())

    result = validate_sitedna(spec)
    print(f"\nConfidence:\n{confidence_summary(result)}")

    # Phase 2: Generate scaffold
    print("\nPhase 2: React Scaffold Generation")
    hr("-")
    output_dir = "./demo-clone"
    gen = ScaffoldGenerator(spec=spec, output_dir=output_dir)
    files = gen.generate()
    total = sum(files.values())
    print(f"  {total} files written to {output_dir}/")
    for category, count in files.items():
        print(f"    {category:<20} {count} file(s)")

    # Phase 3: Visual verification (mock images)
    print("\nPhase 3: Visual Verification (mock)")
    hr("-")
    ref_img = np.random.uniform(0.2, 0.8, (300, 800, 3)).astype(np.float32)
    cand_img = ref_img * 0.92 + np.random.uniform(0, 0.05, ref_img.shape).astype(np.float32)

    verifier = CloseLoopVerifier(ssim_threshold=0.75)
    vr = verifier.verify(
        reference_screenshot=ref_img,
        candidate_screenshot=cand_img,
        reference_palette=[t.__dict__ for t in spec.tokens.palette],
        candidate_palette=[t.__dict__ for t in spec.tokens.palette],
    )
    print(f"  Overall score: {vr.overall_score:.1%}  {'PASS' if vr.passed else 'FAIL'}")
    print(f"  SSIM:          {vr.ssim:.3f}")
    print(f"  Palette dE:    {vr.palette_mean_de:.1f}")
    print(f"  Repair tasks:  {len(vr.repair_tasks)}")

    # Phase 4: Show unresolved
    print("\nPhase 4: Provenance & Unresolved")
    hr("-")
    unresolved = spec.provenance.unresolved
    if unresolved:
        for u in unresolved:
            print(f"  [!] {u}")
    else:
        print("  All captured. No unresolved elements.")

    warnings = result.warnings
    if warnings:
        print("\nWarnings:")
        for w in warnings[:3]:
            print(f"  * {w}")

    print()
    hr()
    print("  Demo complete.")
    print(f"  Clone scaffold: {output_dir}/")
    print("  Run: cd demo-clone && npm install && npm run dev")
    hr()


if __name__ == "__main__":
    main()
