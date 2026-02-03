from __future__ import annotations

from pathlib import Path

from agent.llm_agent_engine import LLMAssistedAgentEngine
from hpa.cli import init_assisted_agent_engine


def test_agent_cli_bootstrap(tmp_path):
    agent_cfg = tmp_path / "agent.yaml"
    agent_cfg.write_text(
        """
        enable_llm_extractor: true
        enable_llm_questioner: true
        enable_llm_refiner: false
        max_questions_per_turn: 1
        fill_only_empty_slots: true
        question_fallback_to_bank: true
        strict_json_only: true
        debug: false
        """.strip()
        + "\n",
        encoding="utf-8",
    )

    llm_cfg = tmp_path / "llm.yaml"
    llm_cfg.write_text(
        """
        base_url: "http://127.0.0.1:8080"
        api_key: ""
        model: "local-model"
        timeout_sec: 60
        temperature: 0.2
        max_tokens: 800
        """.strip()
        + "\n",
        encoding="utf-8",
    )

    root = Path(__file__).resolve().parents[1]
    templates_path = root / "configs" / "templates.yaml"

    engine = init_assisted_agent_engine(templates_path, agent_cfg, llm_cfg)
    assert isinstance(engine, LLMAssistedAgentEngine)
