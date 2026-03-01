from __future__ import annotations

from hpa.config import TemplatesConfig


def missing_slots(state, cfg: TemplatesConfig) -> list[str]:
    mode_key = state.mode_key()
    if not mode_key:
        return []
    required = cfg.required_slots.get(mode_key, [])
    missing = [slot for slot in required if not state.slots.get(slot, "").strip()]
    missing.sort(key=lambda slot: cfg.slot_priority.index(slot) if slot in cfg.slot_priority else 999)
    return missing
