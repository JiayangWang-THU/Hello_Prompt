from __future__ import annotations

from .test_helpers import FakeLLMEnhancer, build_service, make_mode_choice, make_slot_choice


def test_choice_first_flow_prefers_mode_selection_and_number_input():
    llm = FakeLLMEnhancer(
        mode_choice=make_mode_choice("CODE/EXTEND"),
        slot_updates={
            "goal": "把现有 Python CLI 重构成选择题优先的 prompt clarification framework",
            "runtime_env": "Ubuntu 22.04",
            "output_format": "Markdown",
        },
        slot_choice=make_slot_choice("base_system", "现有 Python CLI", "现有命令行工具"),
    )
    service = build_service(llm=llm)

    first = service.handle_user_message("我想重构一个现有 Python CLI 项目，最后输出 Markdown prompt。")
    assert "请选择一个 mode" in first.text

    second = service.handle_user_message("1")
    assert service.state.mode_key() == "CODE/EXTEND"
    assert "更接近下面这些想法之一" in second.text

    third = service.handle_user_message("1")
    assert service.state.confirmed_slots["base_system"] == "现有 Python CLI"


def test_manual_text_is_still_allowed_when_choice_not_enough():
    llm = FakeLLMEnhancer(
        mode_choice=make_mode_choice("CODE/EXTEND"),
        slot_updates={},
        slot_choice=make_slot_choice("goal", "写一个更清晰的 prompt", "生成一份开发说明"),
    )
    service = build_service(llm=llm)

    service.handle_user_message("我想重构一个 CLI 工具")
    service.handle_user_message("1")
    result = service.handle_user_message("我要做的是让 CLI 尽量通过选择题和 LLM 一起完善 prompt。")

    assert "我会尽量" not in result.text
    assert service.state.confirmed_slots["goal"].startswith("我要做的是")
