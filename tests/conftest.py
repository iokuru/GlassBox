import pytest
from glassbox.config import AgentConfig
from glassbox.engine import AgentEngine
from glassbox.executor import CodeExecutor
from glassbox.tool_registry import ToolRegistry


@pytest.fixture
def clean_registry():
    return ToolRegistry()


@pytest.fixture
def executor():
    return CodeExecutor(default_timeout=2.0)


@pytest.fixture
def test_config():
    return AgentConfig(
        max_steps=8,
        timeout_seconds=10.0,
        tool_timeout_seconds=2.0,
        max_retries_per_failure=3,
        model_name="mock-debugger",
    )


@pytest.fixture
def engine(test_config):
    return AgentEngine(config=test_config)
