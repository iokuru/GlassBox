from __future__ import annotations

from typing import Dict, Optional
from glassbox.types import Observation


class DocStoreTool:
    def __init__(self) -> None:
        self._docs: Dict[str, str] = {
            "sys.setrecursionlimit": (
                "sys.setrecursionlimit(limit): Set the maximum depth of the Python interpreter stack. "
                "Default is usually 1000. Warning: Increasing this does not fix infinite recursion bugs."
            ),
            "functools.lru_cache": (
                "functools.lru_cache(maxsize=128, typed=False): Decorator to wrap a function with a memoizing callable "
                "that saves up to the maxsize most recent calls. Useful to speed up recursive algorithms like Fibonacci."
            ),
            "collections.defaultdict": (
                "collections.defaultdict(default_factory): Dict subclass that calls a factory function to supply missing values. "
                "Avoids explicit KeyError checks."
            ),
            "typing.optional": (
                "typing.Optional[X] is equivalent to X | None. Denotes a value that can be None."
            ),
            "dataclasses.dataclass": (
                "dataclasses.dataclass(*, init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False): "
                "Decorator that automatically adds generated special methods like __init__() and __repr__() to user-defined classes."
            ),
        }

    def lookup_documentation(self, topic: str) -> Observation:
        """Fetch exact documentation and signature for standard library modules, functions, or language constructs."""
        if not topic or not topic.strip():
            return Observation(
                content="Error: Topic cannot be empty.",
                is_error=True,
                metadata={"error_type": "invalid_arguments"},
            )

        t = topic.strip().lower()
        for doc_key, content in self._docs.items():
            if t in doc_key.lower() or doc_key.lower() in t:
                return Observation(
                    content=f"Documentation for '{doc_key}':\n{content}",
                    is_error=False,
                    metadata={"topic": topic, "found": True},
                )

        return Observation(
            content=f"No internal doc entry found for '{topic}'. Available topics: {list(self._docs.keys())}",
            is_error=False,
            metadata={"topic": topic, "found": False},
        )
