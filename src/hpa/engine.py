from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hpa.interfaces.cli_agent import build_clarification_service, dispatch_agent_input


@dataclass
class StepResult:
    text: str
    done: bool = False


class AgentEngine:
    """Compatibility wrapper around the unified LLM-driven clarification service."""

    def __init__(self, cfg_path: str | Path = "configs/templates.yaml", assisted: bool = True):
        self.service = build_clarification_service(
            templates_path=cfg_path,
            agent_config_path="configs/agent.yaml",
            llm_config_path="configs/llm.yaml",
        )
        self.warning = None
        self.cfg = self.service.catalog
        self.state = self.service.state

    def reset(self) -> StepResult:
        result = self.service.reset()
        self.state = self.service.state
        return StepResult(text=result.text, done=result.done)

    def step(self, user_text: str) -> StepResult:
        result = dispatch_agent_input(self.service, user_text)
        self.state = self.service.state
        return StepResult(text=result.text, done=result.done)
