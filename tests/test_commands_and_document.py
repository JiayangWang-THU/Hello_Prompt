from __future__ import annotations

import json
from datetime import datetime

from .test_helpers import FakeLLMEnhancer, build_service, make_mode_choice, make_slot_choice


def test_show_clear_export_and_doc(tmp_path, monkeypatch):
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ANN001
            return cls(2024, 1, 2, 3, 4, 5)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("hpa.infrastructure.exporter.datetime", FixedDatetime)

    llm = FakeLLMEnhancer(
        mode_choice=make_mode_choice("CODE/EXTEND"),
        slot_updates={
            "goal": "让 CLI 走选择题优先的 prompt 共创流程",
            "new_features": "P0 选择题交互",
            "compatibility": "保留 /mode /show /export",
            "runtime_env": "Ubuntu 22.04",
            "output_format": "Markdown",
        },
        slot_choice=make_slot_choice("base_system", "现有 Python CLI"),
    )
    service = build_service(llm=llm)
    service.handle_user_message("我要重构一个现有 CLI。")
    service.handle_user_message("1")
    service.handle_user_message("1")

    show = service.show_state()
    assert "当前 mode: CODE/EXTEND" in show.text
    assert "当前等待中的选择题" not in show.text

    doc = service.show_document()
    assert "共享 prompt 文档" in doc.text

    cleared = service.clear_slot("env")
    assert "已清除槽位：runtime_env" in cleared.text

    exported = service.export()
    assert "已导出" in exported.text
    payload = json.loads((tmp_path / "exports" / "session_20240102_030405.json").read_text(encoding="utf-8"))
    assert payload["mode"] == "CODE/EXTEND"
    assert "confirmed_slots" in payload
