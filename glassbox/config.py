from __future__ import annotations

import os
from typing import Optional
from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    max_steps: int = Field(default=12, description="Maximum ReAct loop iterations")
    timeout_seconds: float = Field(default=60.0, description="Overall task timeout in seconds")
    tool_timeout_seconds: float = Field(default=8.0, description="Individual tool timeout in seconds")
    max_retries_per_failure: int = Field(default=3, description="Max retries for a single failure type")
    loop_similarity_threshold: float = Field(default=0.85, description="Threshold for loop stagnation detection")
    model_name: str = Field(default="mock-debugger", description="LLM model identifier")
    api_key: Optional[str] = Field(default=None, description="API key for cloud model provider")
    api_base_url: Optional[str] = Field(default=None, description="Custom base URL for LLM API")
    verbose: bool = Field(default=True, description="Enable verbose logging")

    @classmethod
    def from_env(cls) -> "AgentConfig":
        return cls(
            max_steps=int(os.getenv("GLASSBOX_MAX_STEPS", "12")),
            timeout_seconds=float(os.getenv("GLASSBOX_TIMEOUT", "60.0")),
            tool_timeout_seconds=float(os.getenv("GLASSBOX_TOOL_TIMEOUT", "8.0")),
            max_retries_per_failure=int(os.getenv("GLASSBOX_MAX_RETRIES", "3")),
            model_name=os.getenv("GLASSBOX_MODEL", "mock-debugger"),
            api_key=os.getenv("OPENAI_API_KEY") or os.getenv("GLASSBOX_API_KEY"),
            api_base_url=os.getenv("OPENAI_BASE_URL") or os.getenv("GLASSBOX_BASE_URL"),
        )
