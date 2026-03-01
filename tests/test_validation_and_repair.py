from __future__ import annotations

from hpa.application import RepairService
from hpa.infrastructure import TemplateRepository

from .test_helpers import FakeLLMEnhancer, build_service


def test_validation_detects_missing_section_and_constraints():
    service = build_service(llm=FakeLLMEnhancer())
    service.set_mode("CODE", "EXTEND")
    service.handle_user_message("只说了一个目标")

    template = service.mode_service.current_template(service.state)
    assert template is not None

    result = service.composition_service.compose(service.state, template)
    issues = service.validation_service.validate(template, result)

    issue_codes = {issue.code for issue in issues}
    assert "missing_section" in issue_codes
    assert "missing_required_slot" in issue_codes


def test_repair_graceful_fallback_when_llm_disabled():
    catalog = TemplateRepository("configs/templates.yaml").load()
    template = catalog.get_template("CODE/EXTEND")
    assert template is not None

    service = build_service(
        llm=FakeLLMEnhancer(
            slot_updates={
                "goal": "add prompt growth",
                "base_system": "existing cli",
                "new_features": "P0 refinement",
                "compatibility": "keep current commands",
                "runtime_env": "ubuntu",
                "output_format": "Markdown",
            }
        )
    )
    service.set_mode("CODE", "EXTEND")
    service.handle_user_message("请把这些事实都写进去")

    composed = service.composition_service.compose(service.state, template)
    fallback = service.composition_service.render_prompt(composed.prompt_spec)
    broken = composed.model_copy(update={"prompt_text": "## Goal\n- broken"})
    broken.issues = service.validation_service.validate(template, broken)

    repaired = RepairService(llm=None, enable_repair=False).repair(template, broken, fallback)
    repaired.issues = service.validation_service.validate(template, repaired)

    assert repaired.prompt_text == fallback
    assert repaired.issues == []
