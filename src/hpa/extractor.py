from __future__ import annotations

import json
import re
from typing import Any

from .config import normalize_key_name
from .state import AgentState

_KEYVAL_RE = re.compile(r"^\s*([a-zA-Z_][a-zA-Z0-9_ ]*)\s*[:=]\s*(.+?)\s*$")


def _apply_kv_pairs(state: AgentState, data: dict[str, Any]) -> list[str]:
    updated: list[str] = []
    for raw_key, raw_val in data.items():
        if raw_val is None:
            continue
        key = normalize_key_name(str(raw_key))
        val = str(raw_val).strip()
        if not val:
            continue
        state.slots[key] = val
        updated.append(key)
    return updated


def _extract_from_json(user_text: str) -> dict[str, Any] | None:
    text = user_text.strip()
    if not (text.startswith("{") and text.endswith("}")):
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _extract_from_lines(user_text: str) -> dict[str, Any]:
    pairs: dict[str, Any] = {}
    for line in user_text.splitlines():
        if not line.strip():
            continue
        m = _KEYVAL_RE.match(line)
        if not m:
            continue
        k = m.group(1).strip()
        v = m.group(2).strip()
        pairs[k] = v
    return pairs


def apply_user_message_to_slots(state: AgentState, user_text: str) -> dict:
    """Extractor:
    - JSON object: updates multiple slots.
    - key: value / key=value (single or multi-line): updates matching lines.
    - Fallback: fill last_asked_slot with the full message when no keys found.
    """
    updated: list[str] = []
    filled_freeform = False

    json_data = _extract_from_json(user_text)
    if json_data is not None:
        updated = _apply_kv_pairs(state, json_data)
        return {"updated": updated, "filled_freeform": False}

    kv_pairs = _extract_from_lines(user_text)
    if kv_pairs:
        updated = _apply_kv_pairs(state, kv_pairs)
        return {"updated": updated, "filled_freeform": False}

    if state.last_asked_slot:
        if user_text.strip().startswith("/"):
            return {"updated": [], "filled_freeform": False}
        key = normalize_key_name(state.last_asked_slot)
        if not state.slots.get(key, "").strip():
            state.slots[key] = user_text.strip()
            updated.append(key)
            filled_freeform = True
        state.last_asked_slot = None

    return {"updated": updated, "filled_freeform": filled_freeform}
