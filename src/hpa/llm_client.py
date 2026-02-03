from __future__ import annotations

import json
import urllib.request
from typing import Any, Callable

from .llm_config import LLMConfig


class OpenAICompatibleChatClient:
    def __init__(self, cfg: LLMConfig, opener: Callable = urllib.request.urlopen):
        self.cfg = cfg
        self.opener = opener

    def chat(self, messages: list[dict[str, Any]], **overrides: Any) -> str:
        url = f"{self.cfg.base_url}/v1/chat/completions"
        payload = {
            "model": overrides.get("model", self.cfg.model),
            "temperature": overrides.get("temperature", self.cfg.temperature),
            "max_tokens": overrides.get("max_tokens", self.cfg.max_tokens),
            "messages": messages,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.cfg.api_key:
            headers["Authorization"] = f"Bearer {self.cfg.api_key}"
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")

        with self.opener(request, timeout=self.cfg.timeout_sec) as resp:
            raw = resp.read()

        response = json.loads(raw.decode("utf-8")) if raw else {}
        choices = response.get("choices", [])
        if not choices:
            raise ValueError(f"LLM 响应缺少 choices，keys: {sorted(response.keys())}")
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message", {})
            if isinstance(message, dict):
                content = message.get("content")
                if content:
                    return content
            text = first.get("text")
            if text:
                return text
        raise ValueError(f"LLM 响应缺少内容，keys: {sorted(response.keys())}")
