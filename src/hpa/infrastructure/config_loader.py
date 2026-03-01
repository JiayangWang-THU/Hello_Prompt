from __future__ import annotations

import json
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

DEFAULT_AGENT_CONFIG = {
    "enable_mode_router": True,
    "enable_prompt_refinement": False,
    "enable_validation_repair": True,
    "fill_only_empty_slots": True,
    "strict_json_only": False,
    "max_questions_per_turn": 1,
    "debug": False,
}


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    api_key: str
    model: str
    timeout_sec: int
    temperature: float
    max_tokens: int


@dataclass(frozen=True)
class AgentConfig:
    enable_mode_router: bool
    enable_prompt_refinement: bool
    enable_validation_repair: bool
    fill_only_empty_slots: bool
    strict_json_only: bool
    max_questions_per_turn: int
    debug: bool


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"无法加载配置：{path}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"配置必须是对象：{path}")
    return data


def load_structured_file(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if file_path.suffix.lower() in {".yaml", ".yml"}:
        return _load_yaml(file_path)
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"无法加载配置：{file_path}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"配置必须是对象：{file_path}")
    return data


def _as_bool(value: Any, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False
    raise ValueError(f"{name} 必须是布尔值")


def _as_int(value: Any, name: str) -> int:
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


def _as_float(value: Any, name: str) -> float:
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


def load_llm_config(config_path: str | Path, cli_overrides: dict[str, Any] | None = None) -> LLMConfig:
    path = Path(config_path)
    yaml_data = _load_yaml(path) if path.exists() else {}
    if not path.exists():
        print(f"未找到 LLM 配置文件：{path}，将使用环境变量与默认值。", file=sys.stderr)

    env_data = {
        key: os.environ[env_name]
        for key, env_name in ENV_MAP.items()
        if os.environ.get(env_name) not in {None, ""}
    }
    cli_data = {k: v for k, v in (cli_overrides or {}).items() if v is not None}

    merged = DEFAULT_LLM_CONFIG.copy()
    merged.update(yaml_data)
    merged.update(env_data)
    merged.update(cli_data)

    return LLMConfig(
        base_url=str(merged["base_url"]).rstrip("/"),
        api_key=str(merged["api_key"]),
        model=str(merged["model"]),
        timeout_sec=_as_int(merged["timeout_sec"], "timeout_sec"),
        temperature=_as_float(merged["temperature"], "temperature"),
        max_tokens=_as_int(merged["max_tokens"], "max_tokens"),
    )


def load_agent_config(config_path: str | Path) -> AgentConfig:
    data = _load_yaml(Path(config_path))
    merged = DEFAULT_AGENT_CONFIG.copy()
    merged.update({k: v for k, v in data.items() if v is not None})

    return AgentConfig(
        enable_mode_router=_as_bool(merged["enable_mode_router"], "enable_mode_router"),
        enable_prompt_refinement=_as_bool(
            merged["enable_prompt_refinement"],
            "enable_prompt_refinement",
        ),
        enable_validation_repair=_as_bool(
            merged["enable_validation_repair"],
            "enable_validation_repair",
        ),
        fill_only_empty_slots=_as_bool(merged["fill_only_empty_slots"], "fill_only_empty_slots"),
        strict_json_only=_as_bool(merged["strict_json_only"], "strict_json_only"),
        max_questions_per_turn=_as_int(merged["max_questions_per_turn"], "max_questions_per_turn"),
        debug=_as_bool(merged["debug"], "debug"),
    )
