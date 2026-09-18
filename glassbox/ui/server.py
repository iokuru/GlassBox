from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from glassbox.comparison.langchain_baseline import compare_agents
from glassbox.config import AgentConfig
from glassbox.engine import AgentEngine
from glassbox.failure.injection import FaultType

app = FastAPI(title="GlassBox Live Cognition Visualizer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RunRequest(BaseModel):
    task: str
    fault_type: Optional[str] = None


@app.get("/")
def get_status() -> Dict[str, Any]:
    return {"status": "ok", "service": "GlassBox API Server", "version": "0.2.0"}



@app.post("/api/run")
def run_agent_task(req: RunRequest) -> Dict[str, Any]:
    config = AgentConfig.from_env()
    engine = AgentEngine(config=config)

    if req.fault_type == "rate_limit":
        engine.fault_injector.add_rule("search_web", FaultType.RATE_LIMIT_429, trigger_on_call_count=1)
    elif req.fault_type == "timeout":
        engine.fault_injector.add_rule("run_python_code", FaultType.TIMEOUT, trigger_on_call_count=1)
    elif req.fault_type == "irrelevant":
        engine.fault_injector.add_rule("search_web", FaultType.IRRELEVANT_RESULT, trigger_on_call_count=1)

    trace = engine.run(req.task)
    return trace.model_dump()


@app.post("/api/compare")
def compare_with_baseline(req: RunRequest) -> Dict[str, Any]:
    return compare_agents(req.task, inject_scenario=req.fault_type)


def start_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    import uvicorn
    uvicorn.run("glassbox.ui.server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    start_server()
