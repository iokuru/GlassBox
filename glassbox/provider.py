from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from glassbox.types import Action, Thought


class BaseLLMProvider(ABC):
    @abstractmethod
    def plan(
        self,
        task: str,
        history_context: str,
        available_tools: List[Dict[str, Any]],
        recovery_directive: Optional[str] = None,
    ) -> Tuple[Thought, Optional[Action], bool, Optional[str]]:
        """
        Returns:
            (Thought, Action or None, is_done, final_answer or None)
        """
        pass


class MockDebuggingProvider(BaseLLMProvider):
    """Deterministic simulation provider for debugging agent scenarios and zero-cost testing."""

    def __init__(self) -> None:
        self._call_counter = 0

    def plan(
        self,
        task: str,
        history_context: str,
        available_tools: List[Dict[str, Any]],
        recovery_directive: Optional[str] = None,
    ) -> Tuple[Thought, Optional[Action], bool, Optional[str]]:
        self._call_counter += 1
        h_lower = history_context.lower()

        # Check if previous step completed verification successfully
        if "tests passed" in h_lower or "result: [0, 1, 1, 2, 3, 5, 8]" in h_lower or "status: success" in h_lower:
            thought = Thought(
                content="The sandbox verification passed successfully with expected outputs. The bug has been resolved."
            )
            return (thought, None, True, "Resolved the bug: identified root cause, updated logic, and verified fix in sandbox.")

        # Check for recovery directive
        if recovery_directive and "RATE_LIMITED" in recovery_directive:
            thought = Thought(
                content="Web search is rate limited (HTTP 429). Shifting strategy to consult local documentation store."
            )
            action = Action(
                tool="lookup_documentation",
                params={"topic": "sys.setrecursionlimit"},
                rationale="Fallback to doc_store due to search rate limiting.",
            )
            return (thought, action, False, None)

        if recovery_directive and "IRRELEVANT_RESULT" in recovery_directive:
            thought = Thought(
                content="Previous query was too generic. Reformulating search keywords to specifically target 'recursionerror python'."
            )
            action = Action(
                tool="search_web",
                params={"query": "python recursionerror base case fix"},
                rationale="Mutate search query with precise exception signature.",
            )
            return (thought, action, False, None)

        if recovery_directive and "LOOP_DETECTED" in recovery_directive:
            thought = Thought(
                content="Cognition monitor flagged a repetition loop. Ceasing redundant searches and executing direct code patch."
            )
            fixed_code = (
                "def fib(n, memo=None):\n"
                "    if memo is None:\n"
                "        memo = {}\n"
                "    if n <= 0:\n"
                "        return 0\n"
                "    elif n == 1:\n"
                "        return 1\n"
                "    if n not in memo:\n"
                "        memo[n] = fib(n - 1, memo) + fib(n - 2, memo)\n"
                "    return memo[n]\n\n"
                "assert fib(0) == 0\n"
                "assert fib(1) == 1\n"
                "assert fib(6) == 8\n"
                "print('Tests passed: result:', [fib(i) for i in range(7)])\n"
            )
            action = Action(
                tool="run_python_code",
                params={"code": fixed_code},
                rationale="Break loop by testing corrected implementation with memoization and base case.",
            )
            return (thought, action, False, None)

        # Context-dependent progression
        if "step 1" not in h_lower:
            thought = Thought(
                content="I need to reproduce the issue first by running the failing code snippet in the sandbox."
            )
            code_match = re.search(r"```(?:python)?\n(.*?)```", task, re.DOTALL)
            broken_code = code_match.group(1).strip() if code_match else (
                "def fib(n):\n    return fib(n - 1) + fib(n - 2)\nprint(fib(5))\n"
            )
            if broken_code.startswith("def ") and "print" not in broken_code and "assert" not in broken_code:
                fn_name = broken_code.split()[1].split("(")[0]
                broken_code += f"\nprint({fn_name}(5))\n"

            action = Action(
                tool="run_python_code",
                params={"code": broken_code},
                rationale="Reproduce the failure in isolated sandbox.",
            )
            return (thought, action, False, None)

        if "recursionerror" in h_lower or "maximum recursion depth" in h_lower:
            thought = Thought(
                content="The code failed with RecursionError. Missing base cases for n <= 1. Searching docs for optimal recursion pattern."
            )
            action = Action(
                tool="search_web",
                params={"query": "recursionerror python fix base case"},
                rationale="Look up recursion base case handling.",
            )
            return (thought, action, False, None)

        if "search results" in h_lower or "lookup_documentation" in h_lower or "documentation for" in h_lower:
            thought = Thought(
                content="Documentation advises adding explicit base conditions `if n <= 0: return 0` and `if n == 1: return 1`. Writing and testing fixed code."
            )
            patch_code = (
                "def fib(n):\n"
                "    if n <= 0:\n"
                "        return 0\n"
                "    elif n == 1:\n"
                "        return 1\n"
                "    return fib(n - 1) + fib(n - 2)\n\n"
                "print('Tests passed: result:', [fib(i) for i in range(7)])\n"
            )
            action = Action(
                tool="run_python_code",
                params={"code": patch_code},
                rationale="Run verified patch with base cases.",
            )
            return (thought, action, False, None)

        # Fallback default
        thought = Thought(content="Analyzing current state and verifying logic.")
        return (thought, None, True, "Analysis complete.")


class OpenAICompatibleProvider(BaseLLMProvider):
    """Provider connecting to standard OpenAI / Anthropic / Ollama HTTP completions."""

    def __init__(self, api_key: str, base_url: Optional[str] = None, model: str = "gpt-4o") -> None:
        self.api_key = api_key
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.model = model

    def plan(
        self,
        task: str,
        history_context: str,
        available_tools: List[Dict[str, Any]],
        recovery_directive: Optional[str] = None,
    ) -> Tuple[Thought, Optional[Action], bool, Optional[str]]:
        import requests

        system_prompt = (
            "You are GlassBox, a transparent debugging agent. You solve problems by observing code execution.\n"
            "Format your response as valid JSON with keys:\n"
            "- 'thought': string (your inner reasoning)\n"
            "- 'tool': string (name of tool to use, or null if finished)\n"
            "- 'params': dictionary of tool arguments (or empty dict)\n"
            "- 'is_done': boolean (true if goal is achieved)\n"
            "- 'final_answer': string or null\n"
        )

        user_content = f"TASK:\n{task}\n\nHISTORY:\n{history_context}\n"
        if recovery_directive:
            user_content += f"\n{recovery_directive}\n"

        user_content += f"\nAVAILABLE TOOLS:\n{json.dumps(available_tools, indent=2)}\n"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        resp = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)

        thought = Thought(content=parsed.get("thought", "Thinking..."))
        is_done = parsed.get("is_done", False)
        tool_name = parsed.get("tool")
        final_answer = parsed.get("final_answer")

        if is_done or not tool_name:
            return (thought, None, True, final_answer or "Finished.")

        action = Action(tool=tool_name, params=parsed.get("params", {}))
        return (thought, action, False, None)
