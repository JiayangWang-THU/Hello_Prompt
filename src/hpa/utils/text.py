from __future__ import annotations

import re


def normalize_for_match(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())
