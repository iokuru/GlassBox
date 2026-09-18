import pytest
from glassbox.tool_registry import ToolRegistry
from glassbox.types import Observation


def test_tool_registration_and_execution(clean_registry: ToolRegistry):
    @clean_registry.register(name="add_numbers", description="Add two integers")
    def add(a: int, b: int) -> int:
        return a + b

    assert clean_registry.has_tool("add_numbers")
    obs = clean_registry.execute("add_numbers", {"a": 4, "b": 6})
    assert not obs.is_error
    assert obs.content == "10"
    assert obs.raw_output == 10


def test_tool_not_found(clean_registry: ToolRegistry):
    obs = clean_registry.execute("non_existent_tool", {"x": 1})
    assert obs.is_error
    assert obs.metadata.get("error_type") == "tool_not_found"
    assert "not found" in obs.content


def test_tool_invalid_arguments(clean_registry: ToolRegistry):
    @clean_registry.register(name="greet")
    def greet(name: str) -> str:
        return f"Hello, {name}!"

    # Missing required argument
    obs = clean_registry.execute("greet", {})
    assert obs.is_error
    assert obs.metadata.get("error_type") == "invalid_arguments"


def test_schema_generation(clean_registry: ToolRegistry):
    @clean_registry.register(name="multiply", description="Multiply two numbers")
    def multiply(x: float, y: float) -> float:
        return x * y

    schemas = clean_registry.get_schemas()
    assert len(schemas) == 1
    assert schemas[0]["name"] == "multiply"
    assert "x" in schemas[0]["parameters"]["properties"]
    assert "y" in schemas[0]["parameters"]["properties"]
