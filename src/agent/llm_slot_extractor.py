from __future__ import annotations

from typing import Any

from hpa.config import TemplatesConfig
from hpa.state import AgentState

from .json_utils import extract_first_json_object, safe_parse_json_object

SYSTEM_PROMPT = (
    "You are a structured information extractor for a CODE task.\n"
    "Return ONLY one JSON object. No markdown, no explanation.\n"
    "Schema: {\"updates\": {<key>: <value>, ...}}.\n"
    "Keys must be from allowed_keys. If unsure, omit the key."
)


def _build_user_prompt(
    mode_key: str,
    allowed_keys: list[str],
    slots: dict[str, str],
    user_text: str,
) -> str:
    lines = [
        f"mode_key: {mode_key}",
        f"allowed_keys: {allowed_keys}",
    ]
    if slots:
        lines.append(f"current_slots: {slots}")
    lines.append(f"user_message: {user_text}")
    return "\n".join(lines)


def _is_simple_value(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool))


def extract_slots(
    client,
    cfg: TemplatesConfig,
    state: AgentState,
    user_text: str,
    strict_json_only: bool = True,
) -> dict[str, str]:
    mode_key = state.mode_key()
    if not mode_key:
        return {}

    allowed_keys = set(cfg.required_slots.get(mode_key, [])) | set(cfg.questions.keys())
    if not allowed_keys:
        return {}

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": _build_user_prompt(
                mode_key,
                sorted(allowed_keys),
                {k: v for k, v in state.slots.items() if str(v).strip()},
                user_text,
            ),
        },
    ]

    try:
        response = client.chat(messages)
    except Exception:  # noqa: BLE001
        return {}

    raw_json = response.strip() if strict_json_only else extract_first_json_object(response)
    if not raw_json:
        return {}
    parsed = safe_parse_json_object(raw_json)
    if not parsed:
        return {}
    updates = parsed.get("updates")
    if not isinstance(updates, dict):
        return {}

    result: dict[str, str] = {}
    for raw_key, raw_val in updates.items():
        if not _is_simple_value(raw_val):
            continue
        key = cfg.normalize_key(str(raw_key))
        if key not in allowed_keys:
            continue
        value = str(raw_val).strip()
        if not value:
            continue
        result[key] = value

    return result
