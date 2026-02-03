from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from agent.agent_config import AgentAssistConfig
from agent.llm_agent_engine import LLMAssistedAgentEngine
from hpa.config import TemplatesConfig


class SequenceClient:
    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self._idx = 0

    def chat(self, messages):  # noqa: D401, ANN001
        if self._idx >= len(self._responses):
            return "{}"
        resp = self._responses[self._idx]
        self._idx += 1
        return resp


def _cfg() -> TemplatesConfig:
    root = Path(__file__).resolve().parents[1]
    return TemplatesConfig.load(root / "configs" / "templates.yaml")


def _assist_cfg(**overrides) -> AgentAssistConfig:
    base = {
        "enable_llm_extractor": True,
        "enable_llm_questioner": True,
        "enable_llm_refiner": False,
        "max_questions_per_turn": 1,
        "fill_only_empty_slots": True,
        "question_fallback_to_bank": True,
        "strict_json_only": True,
        "debug": False,
    }
    base.update(overrides)
    return AgentAssistConfig(**base)


def test_fill_only_empty_slots_no_override():
    client = SequenceClient(["{\"updates\": {\"runtime_env\": \"llm-env\"}}"])
    engine = LLMAssistedAgentEngine(_cfg(), _assist_cfg(enable_llm_questioner=False), client)
    engine.step("/mode CODE EXTEND")
    engine.step("runtime_env: ubuntu")
    engine.step("hello")
    assert engine.state.slots["runtime_env"] == "ubuntu"


def test_explicit_override_allowed():
    client = SequenceClient(["{\"updates\": {\"goal\": \"llm-goal\"}}"])
    engine = LLMAssistedAgentEngine(_cfg(), _assist_cfg(enable_llm_questioner=False), client)
    engine.step("/mode CODE EXTEND")
    engine.step("goal: user-goal")
    assert engine.state.slots["goal"] == "llm-goal"


def test_invalid_llm_question_fallback():
    client = SequenceClient(["not json"])
    engine = LLMAssistedAgentEngine(
        _cfg(),
        _assist_cfg(enable_llm_extractor=False, enable_llm_questioner=True),
        client,
    )
    engine.step("/mode CODE EXTEND")
    res = engine.step("hello")
    assert _cfg().questions["goal"] in res.text


def test_clear_alias():
    client = SequenceClient([])
    engine = LLMAssistedAgentEngine(_cfg(), _assist_cfg(enable_llm_extractor=False), client)
    engine.step("/mode CODE EXTEND")
    engine.step("runtime_env: ubuntu")
    res = engine.step("/clear env")
    assert "已清除" in res.text
    assert "runtime_env" not in engine.state.slots


def test_export_contains_fields(tmp_path, monkeypatch):
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: D401, ANN001
            return cls(2024, 1, 2, 3, 4, 5)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("agent.llm_agent_engine.datetime", FixedDatetime)

    client = SequenceClient([])
    engine = LLMAssistedAgentEngine(_cfg(), _assist_cfg(enable_llm_extractor=False), client)
    engine.step("/mode CODE EXTEND")
    res = engine.step("/export")
    assert "已导出" in res.text
    out_path = tmp_path / "exports" / "session_20240102_030405.json"
    assert out_path.exists()
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "CODE/EXTEND"
    assert "slots" in payload
    assert "final_prompt" in payload
    assert "created_at" in payload
