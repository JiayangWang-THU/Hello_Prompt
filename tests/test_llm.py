from __future__ import annotations

import json
from pathlib import Path

from hpa.cli import init_chat_client
from hpa.llm_client import OpenAICompatibleChatClient
from hpa.llm_config import LLMConfig, load_llm_config


def test_llm_config_precedence_yaml(tmp_path, monkeypatch):
    config_path = tmp_path / "llm.yaml"
    config_path.write_text(
        "\n".join(
            [
                "base_url: http://yaml.example",
                "api_key: yaml-key",
                "model: yaml-model",
                "timeout_sec: 10",
                "temperature: 0.3",
                "max_tokens: 111",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("HPA_LLM_BASE_URL", "http://env.example/")
    monkeypatch.setenv("HPA_LLM_MODEL", "env-model")
    monkeypatch.setenv("HPA_LLM_TIMEOUT_SEC", "20")

    cfg = load_llm_config(
        config_path,
        {"model": "cli-model", "max_tokens": 999},
    )

    assert cfg.base_url == "http://env.example"
    assert cfg.model == "cli-model"
    assert cfg.timeout_sec == 20
    assert cfg.max_tokens == 999
    assert cfg.temperature == 0.3


def test_templates_config_yaml_load(tmp_path):
    config_path = tmp_path / "templates.yaml"
    config_path.write_text(
        "\n".join(
            [
                "modes:",
                "  - category: CODE",
                "    subtype: FROM_SCRATCH",
                "  - category: CODE",
                "    subtype: REVIEW",
                "  - category: CODE",
                "    subtype: EXTEND",
                "required_slots:",
                "  CODE/FROM_SCRATCH: [goal, language, runtime_env, scope, interfaces, acceptance_tests, output_format]",
                "  CODE/REVIEW: [goal, repo_context, review_focus, deliverable, output_format]",
                "  CODE/EXTEND: [goal, base_system, new_features, compatibility, runtime_env, output_format]",
                "slot_priority:",
                "  - goal",
                "  - base_system",
                "  - repo_context",
                "  - new_features",
                "  - runtime_env",
                "  - language",
                "  - scope",
                "  - interfaces",
                "  - compatibility",
                "  - review_focus",
                "  - deliverable",
                "  - acceptance_tests",
                "  - output_format",
                "questions: {}",
            ]
        ),
        encoding="utf-8",
    )

    from hpa.config import TemplatesConfig

    cfg = TemplatesConfig.load(config_path)
    assert ("CODE", "FROM_SCRATCH") in cfg.allowed_modes()
    assert "goal" in cfg.required_slots["CODE/EXTEND"]


def _mock_response(payload: dict) -> bytes:
    return json.dumps(payload).encode("utf-8")


class _DummyResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def read(self) -> bytes:
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_llm_client_parse_message_content():
    cfg = LLMConfig(
        base_url="http://localhost:8000",
        api_key="",
        model="m",
        timeout_sec=10,
        temperature=0.2,
        max_tokens=100,
    )

    def opener(request, timeout=10):  # noqa: ARG001
        payload = {"choices": [{"message": {"content": "hello"}}]}
        return _DummyResponse(_mock_response(payload))

    client = OpenAICompatibleChatClient(cfg, opener=opener)
    assert client.chat([{"role": "user", "content": "hi"}]) == "hello"


def test_llm_client_parse_text_fallback():
    cfg = LLMConfig(
        base_url="http://localhost:8000",
        api_key="",
        model="m",
        timeout_sec=10,
        temperature=0.2,
        max_tokens=100,
    )

    def opener(request, timeout=10):  # noqa: ARG001
        payload = {"choices": [{"text": "fallback"}]}
        return _DummyResponse(_mock_response(payload))

    client = OpenAICompatibleChatClient(cfg, opener=opener)
    assert client.chat([{"role": "user", "content": "hi"}]) == "fallback"


def test_chat_bootstrap_init(tmp_path):
    config_path = tmp_path / "llm.yaml"
    config_path.write_text(
        "\n".join(
            [
                "base_url: http://127.0.0.1:8080",
                "api_key: \"\"",
                "model: local-model",
                "timeout_sec: 60",
                "temperature: 0.2",
                "max_tokens: 800",
            ]
        ),
        encoding="utf-8",
    )
    cfg, client = init_chat_client(config_path, {})
    assert cfg.base_url == "http://127.0.0.1:8080"
    assert isinstance(client, OpenAICompatibleChatClient)
