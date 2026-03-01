from __future__ import annotations

import os
from dataclasses import dataclass
from contextlib import contextmanager
from typing import Any
from urllib.parse import urlparse

from hpa.infrastructure.config_loader import LLMConfig


@dataclass
class LegacyChatClient:
    """Fallback client for raw chat mode when langchain-openai is unavailable."""

    cfg: LLMConfig

    def chat(self, messages: list[dict[str, Any]]) -> str:
        from hpa.llm_client import OpenAICompatibleChatClient

        return OpenAICompatibleChatClient(self.cfg).chat(messages)


def build_langchain_chat_model(cfg: LLMConfig):
    try:
        import httpx
        from langchain_openai import ChatOpenAI
    except ImportError as exc:  # pragma: no cover - depends on optional dependency
        raise RuntimeError(
            "langchain-openai 未安装。请安装后再启用 LLM 驱动的 agent。"
        ) from exc

    normalized_base_url = _normalize_openai_base_url(cfg.base_url)
    http_client = None
    http_async_client = None
    if _is_local_base_url(normalized_base_url):
        # Local OpenAI-compatible servers should not depend on shell proxy settings.
        http_client = httpx.Client(trust_env=False)
        http_async_client = httpx.AsyncClient(trust_env=False)

    with _temporary_disable_proxy_env(enabled=_is_local_base_url(normalized_base_url)):
        return ChatOpenAI(
            model=cfg.model,
            api_key=cfg.api_key or "EMPTY",
            base_url=normalized_base_url,
            timeout=cfg.timeout_sec,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            max_retries=0,
            http_client=http_client,
            http_async_client=http_async_client,
        )


def _normalize_openai_base_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/v1"):
        return normalized
    return f"{normalized}/v1"


def _is_local_base_url(base_url: str) -> bool:
    parsed = urlparse(base_url)
    return parsed.hostname in {"127.0.0.1", "localhost", "0.0.0.0"}


@contextmanager
def _temporary_disable_proxy_env(enabled: bool):
    if not enabled:
        yield
        return

    keys = ["all_proxy", "ALL_PROXY", "http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY"]
    backup = {key: os.environ.get(key) for key in keys}
    for key in keys:
        os.environ.pop(key, None)
    try:
        yield
    finally:
        for key, value in backup.items():
            if value is not None:
                os.environ[key] = value
