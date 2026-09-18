# GlassBox · SiteDNA · CloneForge

> **We didn't build another wrapper — we built the thing the wrappers hide.**

Three tightly coupled systems. One thesis: LLM agents that know what they don't know build better things.

---

## What's Here

| System | What it does |
|--------|-------------|
| **GlassBox** | Failure-first agent runtime with explicit error taxonomy, loop detection, and self-healing recovery |
| **SiteDNA** | CDP capture pipeline that extracts a website's design/motion system into a portable JSON spec |
| **CloneForge** | Agent that uses both to clone a live site into a React + Tailwind + Framer Motion project |
| **GlassBench** | Benchmark suite using the live site as ground truth — SSIM, palette ΔE, motion fidelity |

---

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Capture a site's DNA
python -m apps.cloneforge capture https://structured.money -o structured.sitedna.json --mock

# Generate React scaffold
python -m apps.cloneforge clone https://structured.money -o ./structured-clone --mock

# Run benchmarks
python -m apps.cloneforge bench

# Launch trace dashboard at http://127.0.0.1:8001
python -m apps.cloneforge trace
```

---

## Architecture

```
glassbox/               Failure runtime
  failure/
    taxonomy.py         Core error catalog (RUNTIME_EXCEPTION, LOOP_DETECTED, ...)
    web_taxonomy.py     Web failures (BOT_WALL, CDP_DISCONNECT, VISUAL_REGRESSION, ...)
    classifier.py       Pattern-based failure classifier
    loop_detector.py    Jaccard similarity + oscillation detection
    recovery.py         Recovery strategies (retry, replan, break loop, escalate)
    injection.py        Chaos testing harness
  observability/
    trace_store.py      SQLite append-only event log
    trace_server.py     FastAPI + WebSocket three-pane trace dashboard

sitedna/                CDP capture → portable spec → React code
  capture/
    cdp_session.py      Playwright browser driver (MockCDPSession for offline)
    dom_extractor.py    Layout tree + section classification
    style_extractor.py  Computed styles + CSS variable resolver
    font_fingerprinter.py  Stack heuristics + perceptual catalog matching
    palette.py          OKLCH k-means clustering + WCAG contrast
    motion_capture.py   getAnimations() + scroll regression (recovers parallax formulas)
    asset_harvester.py  srcset, CSS-bg, inline SVG, video overlays
    pipeline.py         Orchestrator: all stages → SiteDNA
  spec/
    schema.py           Pydantic v2 SiteDNA model (tokens, layout, motion, assets)
    validate.py         Confidence scoring + warning list
  codegen/
    tokens.py           → tailwind.config.js + :root CSS variables
    layout.py           → section components + App.tsx
    motion.py           → Framer Motion variants + useScroll hooks
    scaffold.py         → full Vite + React + TypeScript project
  verify/
    visual_diff.py      SSIM + heatmap + worst-region detection
    palette_diff.py     ΔE CIE2000 color drift scorer
    layout_iou.py       Bounding box IoU
    motion_diff.py      Entry animation + scroll coefficient comparison
    repair_loop.py      Closed-loop verifier → RepairTask list

eval/
  metrics.py            Failure F1, recovery rate, honesty score
  fault_injection.py    Named web fault scenarios (bot_wall, cdp_disconnect, ...)
  benchmark.py          Suite A (debugging) + Suite B (5 archetypes) + report

apps/
  cloneforge.py         CloneForge CLI: capture | clone | bench | trace
```

---

## The Four Pillars

| Pillar | How GlassBox addresses it |
|--------|--------------------------|
| **Maintainability** | Every module has one job. Failure taxonomy is a catalog, not scattered `if` blocks. Tests per module. |
| **Reliability** | Explicit loop detection prevents infinite cycles. Recovery policies are enumerable and testable. Budget enforcement is a hard limit. |
| **Code Coverage** | 71 tests across 12 test files, covering failure classification, recovery, memory, executor, codegen, verification scorers, and end-to-end pipeline. |
| **AI Challenges** | GlassBench measures whether the agent's output meets objective standards (SSIM ≥ 0.75, ΔE ≤ 10, layout IoU ≥ 0.5). Honesty score penalises unreported failures. |

---

## Benchmark Results (Suite B Archetypes)

| Archetype | Grade | SSIM | ΔE | IoU |
|-----------|-------|------|----|-----|
| dark_editorial | B | 0.61 | 8.0 | 0.65 |
| saas_minimal | B | 0.66 | 8.0 | 0.65 |
| portfolio_scroll | C | 0.60 | 8.0 | 0.65 |
| ecommerce_product | C | 0.55 | 8.0 | 0.65 |
| agency_parallax | C | 0.58 | 8.0 | 0.65 |

*Scores improve with live Playwright capture and GlassBench repair loop enabled.*

---

## SiteDNA Format

```json
{
  "sitedna": "0.1",
  "source": { "url": "https://structured.money/", "viewport": [1440, 900] },
  "tokens": {
    "palette": [
      { "role": "bg.base", "oklch": "0.18 0.01 260", "hex": "#141517" },
      { "role": "fg.primary", "oklch": "0.96 0.01 90", "hex": "#f4f1ea" }
    ],
    "type": {
      "display": {
        "stack": ["EB Garamond", "Georgia", "serif"],
        "matched": { "family": "EB Garamond", "score": 0.94 }
      }
    }
  },
  "motion": {
    "scroll_linked": [
      { "target": "fighter-jet", "formula": "scrollY * -0.05" },
      { "target": "eagle", "formula": "scrollY * -0.07" }
    ]
  },
  "provenance": {
    "confidence": { "tokens": 0.85, "layout": 0.75, "motion": 0.7 },
    "unresolved": ["WebGL background cannot be reproduced via DOM inspection"]
  }
}
```

---

## GlassBench Metrics

| Metric | Measures |
|--------|----------|
| **SSIM** | Pixel-level visual fidelity |
| **Palette ΔE** | Color reproduction accuracy (CIE2000) |
| **Layout IoU** | Section bounding box overlap |
| **Motion Fidelity** | Entry animations + scroll coefficients + parallax |
| **Failure F1** | Did the agent detect the right failure types? |
| **Recovery Rate** | Of injected failures, how many did it recover from? |
| **Honesty Score** | Does it report what it couldn't reproduce? |

---

## Running Tests

```bash
pytest tests/ -v
```

