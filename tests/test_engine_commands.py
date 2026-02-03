from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from hpa.engine import AgentEngine


class _FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):  # noqa: D401, ANN001
        return cls(2024, 1, 2, 3, 4, 5)


def test_clear_slot_command():
    eng = AgentEngine(cfg_path="configs/templates.yaml")
    eng.step("/mode CODE EXTEND")
    eng.step("runtime_env: ubuntu")
    res = eng.step("/clear env")
    assert "已清除" in res.text
    assert "runtime_env" not in eng.state.slots


def test_export_creates_file(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    cfg_path = root / "configs" / "templates.yaml"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("hpa.engine.datetime", _FixedDateTime)

    eng = AgentEngine(cfg_path=cfg_path)
    eng.step("/mode CODE EXTEND")
    eng.step("goal: do something")
    eng.step("base_system: python pkg")
    eng.step("new_features: P0 x")
    eng.step("compatibility: keep old config")
    eng.step("runtime_env: ubuntu")
    eng.step("output_format: Markdown")

    res = eng.step("/export")
    assert "已导出" in res.text
    out_path = tmp_path / "exports" / "session_20240102_030405.json"
    assert out_path.exists()
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "CODE/EXTEND"
    assert "slots" in payload
    assert "prompt" in payload
