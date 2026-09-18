from __future__ import annotations

import re
from typing import Dict, List, Optional
from glassbox.types import Observation


class WebSearchTool:
    def __init__(self) -> None:
        self.knowledge_base: Dict[str, str] = {
            "recursionerror": (
                "Python RecursionError: maximum recursion depth exceeded. Common causes: missing or unreachable "
                "base case in recursive function, cyclic graph traversal without visited set, or excessive depth. "
                "Fix: Add explicit termination condition `if n <= 0: return` or convert recursive stack to an iterative loop."
            ),
            "indexerror": (
                "IndexError: list index out of range. Occurs when trying to access an index >= len(seq) or < -len(seq). "
                "Common in off-by-one errors like `range(len(seq) + 1)` or `i <= len(seq)` instead of `<`. "
                "Fix: Check boundary conditions and verify list length before indexing."
            ),
            "keyerror": (
                "KeyError: Raised when a mapping (dictionary) key is not found in the set of existing keys. "
                "Fix: Use `dict.get(key, default)` or verify presence with `if key in dict:`."
            ),
            "typeerror: unsupported operand": (
                "TypeError: unsupported operand type(s). Happens when attempting arithmetic or concatenation on incompatible types. "
                "Fix: Explicitly cast variables using `int()`, `float()`, or `str()` prior to operation."
            ),
            "zerodivisionerror": (
                "ZeroDivisionError: division by zero. Occurs when divisor expression evaluates to 0. "
                "Fix: Guard with `if divisor == 0:` or provide a default fallback value."
            ),
            "jsondecodeerror": (
                "json.decoder.JSONDecodeError: Expecting value or Unterminated string. "
                "Fix: Clean trailing commas, ensure quotes are double quotes, or wrap payload in `try/except json.JSONDecodeError`."
            ),
            "validationerror": (
                "pydantic.ValidationError: Raised when input data violates field constraints or types. "
                "Fix: Ensure field names match schema or use model_validate with appropriate type coercion."
            ),
        }

    def search_web(self, query: str) -> Observation:
        """Search documentation and developer knowledge bases for error explanations and solutions."""
        if not query or not query.strip():
            return Observation(
                content="Error: Search query cannot be empty.",
                is_error=True,
                metadata={"error_type": "invalid_arguments"},
            )

        q = query.lower()

        if len(q.split()) <= 1 and not any(k in q for k in ["error", "exception", "fix", "python"]):
            return Observation(
                content="Warning: Search query is too broad or ambiguous. Returned 0 high-confidence results.",
                is_error=True,
                metadata={
                    "error_type": "irrelevant_result",
                    "query": query,
                    "suggestion": "Include the specific exception name and context in query.",
                },
            )

        matched_results: List[str] = []
        for key, snippet in self.knowledge_base.items():
            words = key.split()
            if any(word in q for word in words) or key in q:
                matched_results.append(snippet)

        if matched_results:
            combined = "\n\n".join(matched_results[:3])
            return Observation(
                content=f"Search Results for '{query}':\n\n{combined}",
                is_error=False,
                metadata={"query": query, "matches_count": len(matched_results)},
            )

        return Observation(
            content=f"No direct developer documentation found for query '{query}'. Try reformulating search keywords.",
            is_error=False,
            metadata={"query": query, "matches_count": 0},
        )
