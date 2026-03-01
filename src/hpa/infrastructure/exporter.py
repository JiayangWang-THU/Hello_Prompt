from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from hpa.domain import ComposerResult, SessionState


class SessionExporter:
    def __init__(self, export_dir: str | Path = "exports") -> None:
        self.export_dir = Path(export_dir)

    def export_session(self, state: SessionState, result: ComposerResult | None) -> Path:
        self.export_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = self.export_dir / f"session_{timestamp}.json"
        payload = {
            "mode": state.mode_key(),
            "confirmed_slots": state.confirmed_slots,
            "suggestions": [suggestion.model_dump(mode="json") for suggestion in state.suggestions],
            "draft_text": state.draft_text,
            "validation_issues": [issue.model_dump(mode="json") for issue in state.latest_validation_issues],
        }
        if result is not None:
            payload["composer_result"] = result.model_dump(mode="json")
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return out_path
