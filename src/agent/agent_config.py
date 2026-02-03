from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_AGENT_CONFIG = {
    "enable_llm_extractor": True,
    "enable_llm_questioner": True,
    "enable_llm_refiner": False,
    "max_questions_per_turn": 1,
    "fill_only_empty_slots": True,
    "question_fallback_to_bank": True,
    "strict_json_only": True,
    "debug": False,
}


@dataclass(frozen=True)
class AgentAssistConfig:
    enable_llm_extractor: bool
    enable_llm_questioner: bool
    enable_llm_refiner: bool
    max_questions_per_turn: int
    fill_only_empty_slots: bool
    question_fallback_to_bank: bool
    strict_json_only: bool
    debug: bool


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


def load_agent_config(path: str | Path) -> AgentAssistConfig:
    cfg_path = Path(path)
    data: dict[str, Any] = {}
    if cfg_path.exists():
        raw = cfg_path.read_text(encoding="utf-8")
        loaded = yaml.safe_load(raw)
        if loaded is None:
            loaded = {}
        if not isinstance(loaded, dict):
            raise ValueError("agent.yaml 必须是对象")
        data = loaded
    else:
        print(f"未找到 agent 配置文件：{cfg_path}，将使用默认值。", file=sys.stderr)

    merged = DEFAULT_AGENT_CONFIG.copy()
    merged.update({k: v for k, v in data.items() if v is not None})

    enable_llm_extractor = _as_bool(merged["enable_llm_extractor"], "enable_llm_extractor")
    enable_llm_questioner = _as_bool(merged["enable_llm_questioner"], "enable_llm_questioner")
    enable_llm_refiner = _as_bool(merged["enable_llm_refiner"], "enable_llm_refiner")
    fill_only_empty_slots = _as_bool(merged["fill_only_empty_slots"], "fill_only_empty_slots")
    question_fallback_to_bank = _as_bool(merged["question_fallback_to_bank"], "question_fallback_to_bank")
    strict_json_only = _as_bool(merged["strict_json_only"], "strict_json_only")
    debug = _as_bool(merged["debug"], "debug")
    max_questions_per_turn = _as_int(merged["max_questions_per_turn"], "max_questions_per_turn")

    if max_questions_per_turn <= 0:
        raise ValueError("max_questions_per_turn 必须大于 0")

    return AgentAssistConfig(
        enable_llm_extractor=enable_llm_extractor,
        enable_llm_questioner=enable_llm_questioner,
        enable_llm_refiner=enable_llm_refiner,
        max_questions_per_turn=max_questions_per_turn,
        fill_only_empty_slots=fill_only_empty_slots,
        question_fallback_to_bank=question_fallback_to_bank,
        strict_json_only=strict_json_only,
        debug=debug,
    )
