# GlassBox

> *"An Agent That Shows You Its Mind Breaking and Fixing Itself"*

[![Tests](https://img.shields.io/badge/tests-27%20passed-brightgreen.svg)](tests/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![Architecture](https://img.shields.io/badge/architecture-layered%20ReAct-cyan.svg)](glassbox/)

Most agent implementations demo a scripted "happy path" and wrap LLMs in a black box, hiding runtime crashes behind opaque retries or unhandled exceptions. 

**GlassBox makes failure and recovery the actual centerpiece.** Judges and developers can inspect the agent's live cognition trace as it plans, picks a tool, gets burned, classifies its failure, and adapts in real time.

---

## The 4 Engineering Pillars

| Criterion | Implementation in GlassBox |
| :--- | :--- |
| **Maintainability** | Clean layered architecture (`runtime` $\to$ `planner` $\to$ `tools` $\to$ `failure/recovery` $\to$ `memory`). Typed Pydantic models, dependency injection, and decorator-based tool registry (`@registry.register`) make adding new tools or recovery heuristics effortless. |
| **Reliability** | Subprocess code execution isolation, hard timeouts, AST pre-execution validation, Jaccard action-similarity loop detection, and strict wall-clock/step budgets prevent production crashes. |
| **Code Coverage** | Comprehensive test suite covering failure classification, fault injection, loop oscillation heuristics, memory serialization, and end-to-end self-healing scenarios. |
| **AI Standards & Alignment** | Deterministic safety rails, schema verification before execution, prevention of hallucinated tool calls, and automated human escalation if recovery thresholds are exceeded. |

---

## Architectural Blueprint

```
                     User Directive
                           │
                           ▼
                  AgentEngine Loop
                     │          ▲
                     ▼          │
        Planner (Thought / Proposed Action)
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
    Loop Detector         Tool Registry
  (Jaccard / Cycles)     (Schema Binding)
          │                     │
          │                     ▼
          │             Fault Interceptor (Chaos)
          │                     │
          │                     ▼
          │            Code Sandbox / Web Search
          │                     │
          └──────────┬──────────┘
                     ▼
            Observation Handler
          ┌──────────┴──────────┐
          │ Success             │ Error / Anomaly
          ▼                     ▼
       Memory            Failure Classifier
    (Episodic State)     (Taxonomy Matching)
                                │
                                ▼
                         Recovery Engine
                     (Strategy Formulation)
                                │
                                ▼
                       Cognition Directive
```

---

## Quickstart

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/iokuru/GlassBox.git
cd GlassBox

# Install dependencies
pip install -e .
```

### 2. Live Rich Terminal Visualizer

Run the live visual cognition trace in your terminal:

```bash
# Run default debugging scenario
python -m glassbox.ui.cli

# Run with chaos fault injection (e.g. HTTP 429 rate limit)
python -m scenarios.demo_runner --chaos rate_limit

# Run side-by-side LangChain comparison matrix
python -m scenarios.demo_runner --compare --chaos rate_limit
```

### 3. Web Dashboard Visualizer

Launch the real-time web dashboard:

```bash
python -m glassbox.ui.server
```
Open **`http://127.0.0.1:8000`** in your browser.
- Select preset scenarios (RecursionError, 429 Rate Limit Chaos, Stagnation Loop Trap, Timeout Guard).
- Watch the **Mind Break** (red cards) and **Cognition Self-Heal** (green cards) stream in real time.
- Click **"Compare vs LangChain"** for the instant head-to-head comparison.

---

## Failure Taxonomy Reference

GlassBox classifies all runtime anomalies into distinct taxonomy classes defined in [`glassbox/failure/taxonomy.py`](glassbox/failure/taxonomy.py):

- `RATE_LIMITED`: Upstream API returns HTTP 429. Strategy: switch to alternate documentation store or local cache.
- `LOOP_DETECTED`: Repetitive action signatures or tool oscillation. Strategy: forbid repeated invocation and force alternative tool/patch.
- `SYNTAX_ERROR`: Code fails AST parse. Strategy: reconstruct code with valid syntax.
- `RUNTIME_EXCEPTION`: Subprocess raises IndexError, RecursionError, etc. Strategy: mutate code hypothesis.
- `EXECUTION_TIMEOUT`: Execution hangs or runs infinite loop. Strategy: patch environment with iteration guard.
- `IRRELEVANT_RESULT`: Vague search results. Strategy: re-anchor search query with exact error signature.
- `BUDGET_EXCEEDED`: Step count or wall-clock deadline reached. Strategy: terminate and summarize state.

---

## Running the Test Suite

```bash
pytest tests/ -v
```

All 27 test cases validate tool schemas, isolated executors, classification heuristics, loop detectors, and recovery dispatchers.

---

## The Pitch Script

1. **The Hook**: *"Most teams will show you an agent that works on a clean path. But the real test of autonomy is what happens when tools break, rate limits hit, or reasoning loops stall. We built GlassBox — an agent that shows you its mind breaking and fixing itself."*
2. **The Demo**: Trigger the 429 Rate Limit Chaos scenario (`python -m scenarios.demo_runner --chaos rate_limit`).
3. **The Reveal**: Point out the bright red **MIND BREAK: FAILURE DETECTED** banner, followed immediately by the green **SELF-HEAL: ADAPTIVE RECOVERY APPLIED** banner where the agent autonomously redirects to a local doc store and fixes the code.
4. **The Punchline**: *"We didn't build another wrapper — we built the thing the wrappers hide."*
