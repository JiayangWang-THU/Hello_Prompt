from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_LLM_CONFIG = {
    "base_url": "http://127.0.0.1:8080",
    "api_key": "",
    "model": "local-model",
    "timeout_sec": 60,
    "temperature": 0.2,
    "max_tokens": 800,
}

ENV_MAP = {
    "base_url": "HPA_LLM_BASE_URL",
    "api_key": "HPA_LLM_API_KEY",
    "model": "HPA_LLM_MODEL",
    "timeout_sec": "HPA_LLM_TIMEOUT_SEC",
    "temperature": "HPA_LLM_TEMPERATURE",
    "max_tokens": "HPA_LLM_MAX_TOKENS",
}

FIELDS = set(DEFAULT_LLM_CONFIG.keys())


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    api_key: str
    model: str
    timeout_sec: int
    temperature: float
    max_tokens: int


def _parse_int(value: Any, name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} 必须是整数")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError as exc:  # noqa: BLE001
            raise ValueError(f"{name} 必须是整数") from exc
    raise ValueError(f"{name} 必须是整数")


def _parse_float(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} 必须是数字")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError as exc:  # noqa: BLE001
            raise ValueError(f"{name} 必须是数字") from exc
    raise ValueError(f"{name} 必须是数字")


def _select_fields(data: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in data.items() if k in FIELDS and v is not None}


def _load_yaml_config(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
    except Exception:  # noqa: BLE001
        raise ValueError(f"无法加载 LLM 配置：{path}")
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError("llm.yaml 必须是对象")
    return _select_fields(data)


def _load_env_config() -> dict[str, Any]:
    data: dict[str, Any] = {}
    for key, env_name in ENV_MAP.items():
        raw = os.environ.get(env_name)
        if raw is None or raw == "":
            continue
        data[key] = raw
    return data


def _apply_types(values: dict[str, Any]) -> dict[str, Any]:
    typed: dict[str, Any] = {}
    for key, value in values.items():
        if key == "timeout_sec":
            typed[key] = _parse_int(value, "timeout_sec")
        elif key == "max_tokens":
            typed[key] = _parse_int(value, "max_tokens")
        elif key == "temperature":
            typed[key] = _parse_float(value, "temperature")
        else:
            typed[key] = str(value)
    return typed


def load_llm_config(config_path: str | Path, cli_overrides: dict) -> LLMConfig:
    path = Path(config_path)
    yaml_data: dict[str, Any] = {}
    if path.exists():
        yaml_data = _load_yaml_config(path)
    else:
        print(f"未找到 LLM 配置文件：{path}，将使用环境变量与默认值。", file=sys.stderr)

    env_data = _load_env_config()
    cli_data = _select_fields(cli_overrides or {})

    merged = DEFAULT_LLM_CONFIG.copy()
    merged.update(_apply_types(yaml_data))
    merged.update(_apply_types(env_data))
    merged.update(_apply_types(cli_data))

    base_url = str(merged["base_url"]).rstrip("/")
    if not base_url:
        raise ValueError("base_url 不能为空")

    timeout_sec = _parse_int(merged["timeout_sec"], "timeout_sec")
    temperature = _parse_float(merged["temperature"], "temperature")
    max_tokens = _parse_int(merged["max_tokens"], "max_tokens")

    if timeout_sec <= 0:
        raise ValueError("timeout_sec 必须大于 0")
    if temperature < 0:
        raise ValueError("temperature 不能为负数")
    if max_tokens <= 0:
        raise ValueError("max_tokens 必须大于 0")

    return LLMConfig(
        base_url=base_url,
        api_key=str(merged["api_key"]),
        model=str(merged["model"]),
        timeout_sec=timeout_sec,
        temperature=temperature,
        max_tokens=max_tokens,
    )
