from __future__ import annotations

from typing import List
from .state import AgentState
from .config import TemplatesConfig


def missing_slots(state: AgentState, cfg: TemplatesConfig) -> List[str]:
    mode_key = state.mode_key()
    if not mode_key:
        return []
    req = cfg.required_slots.get(mode_key, [])
    miss = [s for s in req if not state.slots.get(s, "").strip()]
    miss.sort(key=lambda s: cfg.slot_priority.index(s) if s in cfg.slot_priority else 999)
    return miss
