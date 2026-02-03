from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

KEY_ALIASES = {
    "env": "runtime_env",
    "os": "runtime_env",
    "output": "output_format",
    "format": "output_format",
    "tests": "acceptance_tests",
    "repo": "repo_context",
    "context": "repo_context",
    "features": "new_features",
    "compat": "compatibility",
    "system": "base_system",
}


def normalize_key_name(key: str) -> str:
    normalized = key.strip().lower()
    return KEY_ALIASES.get(normalized, normalized)


@dataclass(frozen=True)
class TemplatesConfig:
    modes: List[Dict[str, str]]
    required_slots: Dict[str, List[str]]
    slot_priority: List[str]
    questions: Dict[str, str]

    @staticmethod
    def load(path: str | Path) -> "TemplatesConfig":
        p = Path(path)
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"无法加载模板配置：{p}") from exc

        if not isinstance(data, dict):
            raise ValueError("templates.json 必须是 JSON 对象")

        modes = data.get("modes")
        if not isinstance(modes, list) or not modes:
            raise ValueError("modes 必须是非空列表")

        required_slots = data.get("required_slots")
        if not isinstance(required_slots, dict):
            raise ValueError("required_slots 必须是对象")

        slot_priority = data.get("slot_priority")
        if not isinstance(slot_priority, list):
            raise ValueError("slot_priority 必须是列表")

        questions = data.get("questions")
        if questions is None:
            questions = {}
        if not isinstance(questions, dict):
            raise ValueError("questions 必须是对象")

        normalized_modes: list[dict[str, str]] = []
        mode_keys: list[str] = []
        for m in modes:
            if not isinstance(m, dict):
                raise ValueError("modes 中每个条目必须是对象")
            cat = str(m.get("category", "")).strip().upper()
            sub = str(m.get("subtype", "")).strip().upper()
            if not cat or not sub:
                raise ValueError("modes 中每个条目必须包含 category 和 subtype")
            normalized_modes.append({
                "category": cat,
                "subtype": sub,
                "label": str(m.get("label", "")).strip(),
            })
            mode_keys.append(f"{cat}/{sub}")

        normalized_required: dict[str, list[str]] = {}
        for k, v in required_slots.items():
            if not isinstance(v, list):
                raise ValueError(f"required_slots[{k}] 必须是列表")
            key = str(k).strip().upper()
            normalized_required[key] = [normalize_key_name(str(s)) for s in v]

        missing_modes = [k for k in mode_keys if k not in normalized_required]
        if missing_modes:
            raise ValueError(f"required_slots 缺少模式：{', '.join(missing_modes)}")

        normalized_priority = [normalize_key_name(str(s)) for s in slot_priority]

        required_all = {s for req in normalized_required.values() for s in req}
        missing_in_priority = sorted(required_all - set(normalized_priority))
        if missing_in_priority:
            warnings.warn(
                "slot_priority 未包含以下必填槽位，将按末尾顺序处理："
                + ", ".join(missing_in_priority),
                stacklevel=2,
            )

        normalized_questions = {normalize_key_name(str(k)): str(v) for k, v in questions.items()}
        for slot in required_all:
            if slot not in normalized_questions:
                normalized_questions[slot] = f"请补充：{slot}"

        return TemplatesConfig(
            modes=normalized_modes,
            required_slots=normalized_required,
            slot_priority=normalized_priority,
            questions=normalized_questions,
        )

    def normalize_key(self, key: str) -> str:
        return normalize_key_name(key)

    def allowed_modes(self) -> set[Tuple[str, str]]:
        return {(m["category"].upper(), m["subtype"].upper()) for m in self.modes}

    def mode_menu_text(self) -> str:
        lines = ["请选择模式（纯手动模板）："]
        for i, m in enumerate(self.modes, 1):
            lines.append(f'{i}) /mode {m["category"]} {m["subtype"]}  （{m.get("label","")}）')
        lines.append("示例：/mode CODE EXTEND")
        return "\n".join(lines)
