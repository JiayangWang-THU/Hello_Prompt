from __future__ import annotations

from pathlib import Path

from agent.llm_questioner import generate_questions
from hpa.config import TemplatesConfig
from hpa.state import AgentState


class DummyClient:
    def __init__(self, response: str):
        self.response = response

    def chat(self, messages):  # noqa: D401, ANN001
        return self.response


def _cfg() -> TemplatesConfig:
    root = Path(__file__).resolve().parents[1]
    return TemplatesConfig.load(root / "configs" / "templates.yaml")


def test_llm_questioner_filters_invalid_slot():
    state = AgentState(category="CODE", subtype="EXTEND")
    client = DummyClient("{\"ask\": [{\"slot\": \"compatibility\", \"question\": \"?\"}]}")
    questions = generate_questions(client, _cfg(), state, ["goal"])
    assert questions == []


def test_llm_questioner_valid():
    state = AgentState(category="CODE", subtype="EXTEND")
    client = DummyClient("{\"ask\": [{\"slot\": \"goal\", \"question\": \"Describe the goal\"}]}")
    questions = generate_questions(client, _cfg(), state, ["goal"])
    assert questions[0]["slot"] == "goal"
    assert questions[0]["question"] == "Describe the goal"
