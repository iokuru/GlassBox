from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional

from sitedna.capture.pipeline import CapturePipeline, capture_sync
from sitedna.codegen.scaffold import ScaffoldGenerator
from sitedna.spec.validate import validate_sitedna, confidence_summary
from sitedna.verify.repair_loop import CloseLoopVerifier


BANNER = r"""
   ____ _                  _____
  / ___| | ___  _ __   ___|  ___|__  _ __ __ _  ___
 | |   | |/ _ \| '_ \ / _ \ |_ / _ \| '__/ _` |/ _ \
 | |___| | (_) | | | |  __/  _| (_) | | | (_| |  __/
  \____|_|\___/|_| |_|\___|_|  \___/|_|  \__, |\___|
                                           |___/
  GlassBox x SiteDNA — Site-to-React Cloning Agent
"""


def cmd_capture(args: argparse.Namespace) -> None:
    print(BANNER)
    url = args.url
    output = args.output or f"{_url_to_slug(url)}.sitedna.json"
    use_mock = getattr(args, "mock", False)

    print(f"Capturing: {url}")
    print(f"Output:    {output}")
    print()

    try:
        spec = capture_sync(url, output=output, use_mock=use_mock)

        result = validate_sitedna(spec)
        if not result.valid:
            print("\nErrors:")
            for err in result.errors:
                print(f"  ERROR: {err}")
            sys.exit(1)

        print(f"\nDone. SiteDNA saved to: {output}")
        print(f"Sections: {len(spec.layout.sections)}")
        print(f"Colors:   {len(spec.tokens.palette)}")
        print(f"Assets:   {len(spec.assets)}")
        print(f"Animations: {len(spec.motion.entry)} entry, {len(spec.motion.scroll_linked)} scroll, {len(spec.motion.mouse_parallax)} parallax")
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)


def cmd_clone(args: argparse.Namespace) -> None:
    print(BANNER)
    url = args.url
    output_dir = args.output or f"./{_url_to_slug(url)}-clone"
    sitedna_file = getattr(args, "from_spec", None)
    use_mock = getattr(args, "mock", False)

    if sitedna_file and Path(sitedna_file).exists():
        print(f"Loading existing SiteDNA spec: {sitedna_file}")
        from sitedna.spec.schema import SiteDNA
        with open(sitedna_file, encoding="utf-8") as f:
            spec = SiteDNA.model_validate(json.load(f))
    else:
        print(f"Capturing SiteDNA from: {url}")
        spec = capture_sync(url, use_mock=use_mock)

    print(f"\nGenerating React scaffold to: {output_dir}")
    gen = ScaffoldGenerator(spec=spec, output_dir=output_dir)
    files = gen.generate()

    total = sum(files.values())
    print(f"\nScaffold generated: {total} files written")
    for category, count in files.items():
        print(f"  {category:<20} {count} file(s)")

    print(f"\nNext steps:")
    print(f"  cd {output_dir}")
    print(f"  npm install")
    print(f"  npm run dev")
    print()

    if not use_mock:
        print("  Place harvested assets in public/assets/ then run GlassBench:")
        print(f"  python -m eval.benchmark --url {url} --clone-dir {output_dir}")


def cmd_bench(args: argparse.Namespace) -> None:
    from eval.benchmark import SuiteARunner, SuiteBRunner, generate_report, save_report
    from sitedna.capture.pipeline import capture_sync

    print(BANNER)
    print("Running GlassBench...\n")
    print("Suite A: Failure Detection & Recovery")

    runner_a = SuiteARunner()
    results_a = runner_a.run_all(engine_factory=_make_engine)

    print("\nSuite B: Visual Cloning Fidelity")
    runner_b = SuiteBRunner()
    results_b = runner_b.run_all(capture_fn=capture_sync)

    report = generate_report(results_a, results_b)
    print(report)
    save_report(results_a, results_b)


def cmd_trace(args: argparse.Namespace) -> None:
    from glassbox.observability.trace_server import run_trace_server
    port = getattr(args, "port", 8001)
    run_trace_server(port=port)


def _make_engine(scenario_id: str) -> any:
    from glassbox.config import AgentConfig
    from glassbox.engine import AgentEngine
    from glassbox.tool_registry import ToolRegistry
    from glassbox.tools.code_sandbox import CodeSandboxTool
    from glassbox.tools.web_search import WebSearchTool
    from glassbox.tools.doc_store import DocStoreTool
    from glassbox.provider import MockDebuggingProvider
    from glassbox.memory import AgentMemory
    from glassbox.planner import Planner
    from glassbox.failure.classifier import FailureClassifier
    from glassbox.failure.recovery import RecoveryEngine
    from glassbox.failure.loop_detector import LoopDetector
    from glassbox.failure.injection import FaultInjector

    config = AgentConfig(max_steps=15, step_budget=15)
    registry = ToolRegistry()
    CodeSandboxTool().register(registry)
    WebSearchTool().register(registry)
    DocStoreTool().register(registry)

    from scenarios import recursion_error, index_out_of_range
    task_map = {
        "recursion_error": recursion_error.TASK_DESCRIPTION,
        "index_out_of_range": index_out_of_range.TASK_DESCRIPTION,
    }
    task = task_map.get(scenario_id, f"Debug {scenario_id}")

    provider = MockDebuggingProvider()
    memory = AgentMemory(window_size=20)
    planner = Planner(provider=provider, registry=registry)
    classifier = FailureClassifier()
    recovery = RecoveryEngine()
    loop_detector = LoopDetector()
    injector = FaultInjector()

    return AgentEngine(
        task=task,
        config=config,
        registry=registry,
        planner=planner,
        memory=memory,
        classifier=classifier,
        recovery_engine=recovery,
        loop_detector=loop_detector,
        fault_injector=injector,
    )


def _url_to_slug(url: str) -> str:
    slug = url.replace("https://", "").replace("http://", "").replace("/", "-").rstrip("-")
    return slug[:40]


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="cloneforge",
        description="GlassBox + SiteDNA site-to-React cloning agent",
    )
    subparsers = parser.add_subparsers(dest="command")

    cap = subparsers.add_parser("capture", help="Capture SiteDNA spec from a live URL")
    cap.add_argument("url", help="Target URL")
    cap.add_argument("-o", "--output", help="Output path for .sitedna.json")
    cap.add_argument("--mock", action="store_true", help="Use mock offline capture")
    cap.set_defaults(func=cmd_capture)

    clone = subparsers.add_parser("clone", help="Clone a site to React scaffold")
    clone.add_argument("url", help="Target URL")
    clone.add_argument("-o", "--output", help="Output directory for React project")
    clone.add_argument("--from-spec", dest="from_spec", help="Load existing .sitedna.json instead of capturing")
    clone.add_argument("--mock", action="store_true", help="Use mock offline capture")
    clone.set_defaults(func=cmd_clone)

    bench = subparsers.add_parser("bench", help="Run GlassBench evaluation suite")
    bench.set_defaults(func=cmd_bench)

    trace = subparsers.add_parser("trace", help="Launch trace server dashboard")
    trace.add_argument("--port", type=int, default=8001)
    trace.set_defaults(func=cmd_trace)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
