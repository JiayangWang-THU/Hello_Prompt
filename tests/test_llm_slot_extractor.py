from __future__ import annotations

from pathlib import Path

from agent.llm_slot_extractor import extract_slots
from hpa.config import TemplatesConfig
from hpa.state import AgentState


class DummyClient:
    def __init__(self, response: str):
        self.response = response

    def chat(self, messages):  # noqa: D401, ANN001
        return self.response


def _cfg() -> TemplatesConfig:
    root = Path(__file__).resolve().parents[1]
    return TemplatesConfig.load(root / 'configs' / 'templates.yaml')


def test_llm_slot_extractor_valid_updates():
    state = AgentState(category='CODE', subtype='EXTEND')
    client = DummyClient('{"updates": {"goal": "Build", "env": "Ubuntu", "bad": "x"}}')
    updates = extract_slots(client, _cfg(), state, 'User says goal and env')
    assert updates['goal'] == 'Build'
    assert updates['runtime_env'] == 'Ubuntu'
    assert 'bad' not in updates


def test_llm_slot_extractor_invalid_json():
    state = AgentState(category='CODE', subtype='EXTEND')
    client = DummyClient('not json')
    updates = extract_slots(client, _cfg(), state, 'User says')
    assert updates == {}
