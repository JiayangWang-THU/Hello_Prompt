from __future__ import annotations

import json
from typing import Any


def extract_first_json_object(text: str) -> str | None:
    in_string = False
    escape = False
    depth = 0
    start = None

    for idx, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            if depth == 0:
                start = idx
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    return text[start: idx + 1]
    return None


def safe_parse_json_object(text: str) -> dict[str, Any] | None:
    try:
        data = json.loads(text)
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(data, dict):
        return None
    return data
