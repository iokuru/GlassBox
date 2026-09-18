from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from glassbox.provider import BaseLLMProvider
from glassbox.tool_registry import ToolRegistry
from glassbox.types import Action, Thought


class Planner:
    def __init__(self, provider: BaseLLMProvider, registry: ToolRegistry) -> None:
        self.provider = provider
        self.registry = registry

    def decide_next_step(
        self,
        task: str,
        history_context: str,
        recovery_directive: Optional[str] = None,
    ) -> Tuple[Thought, Optional[Action], bool, Optional[str]]:
        tool_schemas = self.registry.get_schemas()
        thought, action, is_done, final_answer = self.provider.plan(
            task=task,
            history_context=history_context,
            available_tools=tool_schemas,
            recovery_directive=recovery_directive,
        )

        if is_done or action is None:
            return (thought, None, True, final_answer)

        # Validate action against registry
        if not self.registry.has_tool(action.tool):
            # Annotate thought to reflect mismatch
            thought.content += f" [Note: Model requested unknown tool '{action.tool}']"

        return (thought, action, False, None)
