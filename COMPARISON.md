# GlassBox vs. Standard ReAct Frameworks (LangChain Pattern)

> *"We didn't build another wrapper &mdash; we built the thing the wrappers hide."*

This document provides a technical comparison between conventional agent wrappers (e.g. LangChain's `AgentExecutor` or standard ReAct loops) and the **GlassBox** architecture.

---

## 1. Architectural Differences

| Capability | Standard ReAct (e.g. LangChain `AgentExecutor`) | GlassBox Architecture |
| :--- | :--- | :--- |
| **Failure Taxonomy** | **None**: Failures are string observations fed back into the next prompt, or raise uncaught Python exceptions. | **Explicit Taxonomy Catalog**: Distinguishes between `RATE_LIMITED`, `SYNTAX_ERROR`, `TIMEOUT`, `LOOP_DETECTED`, `IRRELEVANT_RESULT`, and `INVALID_ARGUMENTS`. |
| **Loop & Stagnation Detection** | **None**: Relies solely on reaching `max_iterations`, burning tokens on repeated broken calls. | **Jaccard Similarity + Oscillation Heuristics**: Detects identical action signatures and cyclical tool traps ($A \to B \to A \to B$). |
| **Self-Healing Policies** | **Passive**: Re-prompts the model with the raw error string, hoping the LLM notices. | **Active Adaptation Engine**: Injects explicit system directives: query mutation, alternative tool fallback, environment patching, or human escalation. |
| **Subprocess Isolation** | **Often Inline**: Tools running arbitrary code can crash the host process or hang indefinitely. | **Subprocess Sandbox**: Strict timeouts, AST pre-validation, output buffer limits, and cleanup routines. |
| **Budget Enforcement** | Step count only. | Wall-clock time, step limits, per-tool timeouts, and retry thresholds. |
| **Cognition Observability** | Raw console logs or opaque JSON traces. | Live visual streaming (Rich Terminal UI + Web SSE Dashboard) highlighting **Mind Breaks** in red and **Self-Heals** in green. |

---

## 2. Real-World Failure Case Studies

### Scenario A: Upstream 429 Rate Limit
- **Standard ReAct (LangChain)**:
  1. Calls `search_web`.
  2. Search returns `HTTP 429 Client Error: Too Many Requests`.
  3. The agent executor either crashes with an unhandled exception or feeds `"HTTP 429..."` into the LLM prompt.
  4. The LLM repeats the search call, gets blocked again, and exhausts max iterations.
- **GlassBox**:
  1. Calls `search_web` $\to$ receives HTTP 429.
  2. `FailureClassifier` classifies the failure as `FailureType.RATE_LIMITED` (Severity: `HIGH`).
  3. `RecoveryEngine` prescribes `RecoveryAction.SWITCH_TOOL`.
  4. System injects a cognition directive: `"Search endpoint rate limited. Shifting to local doc_store."`
  5. Planner immediately switches to `lookup_documentation`, retrieves needed signatures, and completes the task.

### Scenario B: Recursive Stagnation Loop
- **Standard ReAct (LangChain)**:
  1. The agent calls `search_web` with `"python recursion fix"`.
  2. The agent calls `search_web` with `"python recursion fix base case"`.
  3. The agent calls `search_web` with `"python recursion fix"`.
  4. It burns through step budget without testing code or making progress.
- **GlassBox**:
  1. `LoopDetector` evaluates action history with Jaccard token similarity ($\ge 0.85$).
  2. Traps repetition before execution: flags `FailureType.LOOP_DETECTED`.
  3. `RecoveryEngine` applies `RecoveryAction.BREAK_LOOP`, for bidding `search_web` and locking candidate tools to `['run_python_code', 'lookup_documentation']`.
  4. The planner is forced out of its cognitive loop, writes the unit test patch, and verifies it in the sandbox.

---

## 3. What LangChain Did Silently That We Solved

When building an autonomous agent from scratch, standard libraries hide the most difficult reliability questions:

```
[Standard Framework]:  Observation: Exception: 429 Rate Limit  --->  Silent Retry / Infinite Loop / Silent Crash
[GlassBox]:            Observation  --->  Classifier  --->  Taxonomy Match  --->  Policy Dispatch  --->  Cognition Trace
```

By lifting failures into an observable, structured taxonomy, GlassBox turns agent brittle points into verifiable self-healing moments.
