from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from glassbox.failure.injection import FaultInjector, FaultRule, FaultType


WEB_FAULT_SCENARIOS: Dict[str, List[Dict[str, Any]]] = {
    "bot_wall": [
        {
            "fault_type": "RATE_LIMIT_429",
            "trigger_pattern": "navigate",
            "description": "Simulate Cloudflare 403 on navigation",
            "probability": 1.0,
        }
    ],
    "cdp_disconnect": [
        {
            "fault_type": "TIMEOUT",
            "trigger_pattern": "cdp",
            "description": "Simulate CDP session timeout",
            "probability": 0.8,
        }
    ],
    "lazy_content": [
        {
            "fault_type": "MALFORMED_OUTPUT",
            "trigger_pattern": "dom_extract",
            "description": "Return incomplete DOM (IntersectionObserver not fired)",
            "probability": 1.0,
        }
    ],
    "modal_occlusion": [
        {
            "fault_type": "MALFORMED_OUTPUT",
            "trigger_pattern": "screenshot",
            "description": "Screenshot shows modal covering content",
            "probability": 1.0,
        }
    ],
    "combined_hard": [
        {
            "fault_type": "RATE_LIMIT_429",
            "trigger_pattern": "navigate",
            "description": "Initial bot-wall followed by CDP instability",
            "probability": 0.5,
        },
        {
            "fault_type": "TIMEOUT",
            "trigger_pattern": "cdp",
            "description": "CDP disconnect after bot-wall cleared",
            "probability": 0.6,
        },
    ],
}


@dataclass
class InjectionRecord:
    scenario: str
    faults_injected: List[str] = field(default_factory=list)
    faults_recovered: List[str] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None

    def recovery_rate(self) -> float:
        if not self.faults_injected:
            return 1.0
        return len(self.faults_recovered) / len(self.faults_injected)


class WebFaultInjector:
    def __init__(self, scenario: str = "bot_wall") -> None:
        self.scenario = scenario
        self.record = InjectionRecord(scenario=scenario)
        self._rules = WEB_FAULT_SCENARIOS.get(scenario, [])

    def should_inject(self, action_name: str) -> Optional[Dict[str, Any]]:
        import random
        for rule in self._rules:
            pattern = rule.get("trigger_pattern", "")
            prob = rule.get("probability", 0.5)
            if pattern.lower() in action_name.lower() and random.random() < prob:
                fault_type = rule.get("fault_type", "TIMEOUT")
                self.record.faults_injected.append(fault_type)
                return {
                    "fault_type": fault_type,
                    "description": rule.get("description", ""),
                    "error_message": f"[INJECTED] {rule.get('description', 'fault')}",
                }
        return None

    def mark_recovered(self, fault_type: str) -> None:
        self.record.faults_recovered.append(fault_type)

    def finish(self) -> InjectionRecord:
        self.record.ended_at = time.time()
        return self.record

    def list_scenarios() -> List[str]:
        return list(WEB_FAULT_SCENARIOS.keys())
