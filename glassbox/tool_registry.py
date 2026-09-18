from __future__ import annotations

import inspect
import time
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, ConfigDict

from glassbox.types import Observation


class ToolDefinition(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str
    parameters_schema: Dict[str, Any]
    handler: Any = None


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, ToolDefinition] = {}

    def register(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        parameters_schema: Optional[Dict[str, Any]] = None,
    ) -> Callable:
        def decorator(fn: Callable) -> Callable:
            tool_name = name or fn.__name__
            tool_desc = description or (fn.__doc__.strip() if fn.__doc__ else "No description")
            schema = parameters_schema or self._extract_schema_from_signature(fn)

            self._tools[tool_name] = ToolDefinition(
                name=tool_name,
                description=tool_desc,
                parameters_schema=schema,
                handler=fn,
            )
            return fn

        return decorator

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def list_tools(self) -> List[ToolDefinition]:
        return list(self._tools.values())

    def get_schemas(self) -> List[Dict[str, Any]]:
        schemas = []
        for tool in self._tools.values():
            schemas.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters_schema,
            })
        return schemas

    def execute(self, tool_name: str, params: Dict[str, Any]) -> Observation:
        start_time = time.perf_counter()
        tool = self.get(tool_name)

        if not tool:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return Observation(
                content=f"Error: Tool '{tool_name}' not found. Available tools: {list(self._tools.keys())}",
                is_error=True,
                execution_time_ms=duration_ms,
                metadata={"tool_name": tool_name, "error_type": "tool_not_found"},
            )

        try:
            validated_params = self._validate_and_bind_params(tool, params)
            result = tool.handler(**validated_params)
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            if isinstance(result, Observation):
                result.execution_time_ms = duration_ms
                return result

            return Observation(
                content=str(result),
                is_error=False,
                raw_output=result,
                execution_time_ms=duration_ms,
                metadata={"tool_name": tool_name},
            )

        except TypeError as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return Observation(
                content=f"Argument error executing '{tool_name}': {str(e)}",
                is_error=True,
                execution_time_ms=duration_ms,
                metadata={"tool_name": tool_name, "error_type": "invalid_arguments", "raw_error": str(e)},
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return Observation(
                content=f"Execution error in '{tool_name}': {type(e).__name__}: {str(e)}",
                is_error=True,
                execution_time_ms=duration_ms,
                metadata={"tool_name": tool_name, "error_type": "runtime_exception", "raw_error": str(e)},
            )

    def _validate_and_bind_params(self, tool: ToolDefinition, params: Dict[str, Any]) -> Dict[str, Any]:
        sig = inspect.signature(tool.handler)
        bound = sig.bind_partial(**params)
        bound.apply_defaults()
        return bound.arguments

    def _extract_schema_from_signature(self, fn: Callable) -> Dict[str, Any]:
        sig = inspect.signature(fn)
        properties = {}
        required = []

        type_mapping = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            dict: "object",
            list: "array",
        }

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue
            param_type = "string"
            if param.annotation != inspect.Parameter.empty:
                param_type = type_mapping.get(param.annotation, "string")

            properties[param_name] = {
                "type": param_type,
                "description": f"Parameter {param_name}",
            }
            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }
