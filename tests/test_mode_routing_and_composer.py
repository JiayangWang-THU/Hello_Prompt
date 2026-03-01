from __future__ import annotations

from hpa.domain import ChoiceOption, ChoicePrompt

from .test_helpers import FakeLLMEnhancer, build_service, make_mode_choice, make_slot_choice


def test_mode_choice_does_not_override_manual_mode():
    llm = FakeLLMEnhancer(mode_choice=make_mode_choice("CODE/REVIEW"))
    service = build_service(llm=llm)

    pre_mode = service.handle_user_message("Can you review this repo?")
    assert "CODE/REVIEW" in pre_mode.text

    service.set_mode("CODE", "EXTEND")
    assert service.state.mode_key() == "CODE/EXTEND"


def test_composer_builds_shared_prompt_document():
    llm = FakeLLMEnhancer(
        slot_updates={
            "goal": "review architecture",
            "repo_context": "src/hpa and tests",
            "review_focus": "architecture and maintainability",
            "deliverable": "prioritized findings",
            "output_format": "Markdown",
        }
    )
    service = build_service(llm=llm)
    service.set_mode("CODE", "REVIEW")
    result = service.handle_user_message("请做一次 review")

    assert result.done is True
    assert service.state.latest_document is not None
    assert any(section.key == "goal" for section in service.state.latest_document.sections)
    assert "## Goal" in result.text


def test_revise_section_uses_choice_prompt():
    revision_choice = ChoicePrompt(
        kind="doc_revision",
        title="请选择 Goal 段的改写方向",
        question="哪种表述更清晰？",
        options=[
            ChoiceOption(key="1", label="更明确的 Goal", value="- 更明确的 goal", rationale="更聚焦"),
            ChoiceOption(key="2", label="更简洁的 Goal", value="- 更简洁的 goal", rationale="更短"),
        ],
        section_key="goal",
        allow_manual_text=True,
        manual_text_hint="也可以自己写。",
    )
    llm = FakeLLMEnhancer(
        slot_updates={
            "goal": "review architecture",
            "repo_context": "src/hpa and tests",
            "review_focus": "architecture",
            "deliverable": "prioritized findings",
            "output_format": "Markdown",
        },
        doc_revision=revision_choice,
    )
    service = build_service(llm=llm)
    service.set_mode("CODE", "REVIEW")
    service.handle_user_message("请做 review")
    revise = service.revise_document("goal")
    assert "请选择 Goal 段的改写方向" in revise.text
    applied = service.handle_user_message("1")
    assert "更明确的 goal" in applied.text
