from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from hpa.domain import ComposerResult, SessionState


class InMemorySessionStore:
    def __init__(self) -> None:
        self._state = SessionState()

    def load(self) -> SessionState:
        return self._state

    def save(self, state: SessionState) -> None:
        self._state = state


class JsonFileSessionStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def save(self, state: SessionState, result: ComposerResult | None = None) -> Path:
        payload = asdict(state)
        if result is not None:
            payload["latest_result"] = result.model_dump(mode="json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return self.path
