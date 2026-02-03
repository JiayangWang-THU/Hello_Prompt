from __future__ import annotations

import re
from .state import AgentState

_KEYVAL_RE = re.compile(r"^\s*([a-zA-Z_]+)\s*[:=]\s*(.+?)\s*$")


def apply_user_message_to_slots(state: AgentState, user_text: str) -> None:
    """Minimal extractor:
    - If user provides `key: value` or `key=value`, fill that slot directly.
    - Else, fill the last asked slot with the whole message.
    """
    m = _KEYVAL_RE.match(user_text)
    if m:
        k = m.group(1).strip()
        v = m.group(2).strip()
        state.slots[k] = v
        return

    if state.last_asked_slot:
        if user_text.strip().startswith("/"):
            return
        state.slots[state.last_asked_slot] = user_text.strip()
        state.last_asked_slot = None
