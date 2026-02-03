from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class TemplatesConfig:
    modes: List[Dict[str, str]]
    required_slots: Dict[str, List[str]]
    slot_priority: List[str]
    questions: Dict[str, str]

    @staticmethod
    def load(path: str | Path) -> "TemplatesConfig":
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        return TemplatesConfig(
            modes=data["modes"],
            required_slots=data["required_slots"],
            slot_priority=data["slot_priority"],
            questions=data["questions"],
        )

    def allowed_modes(self) -> set[Tuple[str, str]]:
        return {(m["category"].upper(), m["subtype"].upper()) for m in self.modes}

    def mode_menu_text(self) -> str:
        lines = ["请选择模式（纯手动模板）："]
        for i, m in enumerate(self.modes, 1):
            lines.append(f'{i}) /mode {m["category"]} {m["subtype"]}  （{m.get("label","")}）')
        lines.append("示例：/mode CODE EXTEND")
        return "\n".join(lines)
