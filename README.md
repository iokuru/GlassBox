# GlassBox

> A transparent autonomous debugging agent runtime with explicit failure taxonomy, action loop detection, and self-healing recovery.

GlassBox is built on a single premise: **LLM agents should not hide their failures behind opaque retry wrappers.** Instead, failures must be explicitly classified into an enumerable taxonomy, trapped before they exhaust token budgets, and resolved through deterministic self-healing policies.

---

## Core Capabilities

- **Structured Failure Taxonomy**: 9 distinct failure types with severity levels, recovery strategies, and root-cause classification.
- **Loop & Oscillation Detection**: Jaccard similarity heuristics and periodic cycle detection ($A \to B \to A \to B$) that break repetitive agent behaviors.
- **Adaptive Self-Healing**: Dynamic tool switching, query mutation, AST patching, and hypothesis invalidation.
- **Chaos Injection Harness**: Programmatic fault injection (rate limits, timeouts, malformed responses) to stress-test agent resiliency.
- **Sandboxed Execution**: Subprocess-level isolation with AST pre-validation and hard timeout guards.
- **Episodic Flight Recorder**: Append-only SQLite event log capturing every thought, action, observation, failure, and recovery with microsecond timestamps.
- **Live Terminal & Streaming UI**: Rich-powered live cognition console and FastAPI WebSocket trace streamer.

---

## Architecture

```
glassbox/
├── config.py             # Agent runtime configuration & environment loading
├── engine.py             # ReAct cognitive loop orchestrator & step budgeting
├── executor.py           # Sandboxed subprocess code execution with timeout guard
├── memory.py             # Episodic memory and execution trace history
├── planner.py            # ReAct reasoning planner & tool router
├── provider.py           # LLM provider layer (MockDebuggingProvider / OpenAI)
├── tool_registry.py      # Schema-validated tool registration engine
├── types.py              # Pydantic core execution domain models
├── comparison/
│   └── langchain_baseline.py  # Head-to-head comparison vs naive ReAct agent
├── failure/
│   ├── classifier.py     # Traceback, status code, and exception pattern classifier
│   ├── injection.py      # Chaos engineering fault injection harness
│   ├── loop_detector.py  # Jaccard n-gram similarity & cycle oscillation detector
│   ├── recovery.py       # Recovery policies (retry, switch tool, replan, break loop)
│   └── taxonomy.py       # Failure catalog and taxonomy descriptors
├── observability/
│   ├── trace_server.py   # FastAPI WebSocket streaming server
│   └── trace_store.py    # SQLite append-only event log
├── tools/
│   ├── code_sandbox.py   # Python execution tool wrapping the sandbox
│   ├── doc_store.py      # In-memory documentation store
│   └── web_search.py     # Mock search engine with query filtering
└── ui/
    ├── cli.py            # Rich terminal live cognition visualizer
    └── server.py         # GlassBox API server
```

---

## The Four Engineering Pillars

| Pillar | Architectural Implementation |
|---|---|
| **Maintainability** | Strict separation of concerns. Every failure policy is registered in a central taxonomy catalog rather than scattered `try/except` blocks. |
| **Reliability** | Hard step budgets prevent runaway execution. Cycle oscillation detectors catch alternating tool traps. Sandbox timeouts kill frozen subprocesses. |
| **Observability** | Every cognitive event (`thought`, `action`, `observation`, `failure`, `recovery`) is persisted to an immutable SQLite flight recorder. |
| **Resilience** | Proven recovery against upstream HTTP 429 rate limits, infinite recursions, syntax errors, and missing tools. |

---

## Getting Started

### Installation

```bash
# Clone the repository
git clone https://github.com/iokuru/GlassBox.git
cd GlassBox

# Install in editable mode
pip install -e ".[dev]"
```

### Quick Run

```bash
# Run the interactive demo runner
python -m scenarios.demo_runner

# Launch the Rich terminal live visualizer
python -m glassbox.ui.cli

# Launch the trace server
glassbox-trace
```

### Running Tests

```bash
pytest tests/ -v
```
