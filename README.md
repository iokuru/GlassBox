# GlassBox

An autonomous agent architecture designed around explicit failure detection, runtime recovery strategies, and live cognition inspection.

Most agent implementations wrap LLMs in a black-box ReAct loop and hide runtime failures behind generic error messages or unhandled exceptions. GlassBox makes failure and recovery the primary architectural concern:

- **Failure Taxonomy**: Classifies tool failures, syntax errors, timeouts, loop stagnation, and hallucinated invocations into distinct failure categories.
- **Autonomous Recovery Strategies**: Applies domain-specific recovery heuristics (argument mutation, tool switching, environment patching, clarification requests).
- **Loop & Stagnation Detection**: Detects repeated action signatures and cyclical reasoning traps using Jaccard action similarity.
- **Budget Enforcement**: Hard caps on wall-clock time, step count, and execution limits to guarantee termination.
- **Live Cognition Trace**: Dual-mode visualization via Rich terminal streaming and real-time web dashboard.
