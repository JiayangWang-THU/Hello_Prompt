from __future__ import annotations

from hpa.domain import ComposerResult, PromptSpec, TemplateCatalog, TemplateSpec, ValidationIssue
from hpa.utils.text import normalize_for_match


class ValidationService:
    def __init__(self, catalog: TemplateCatalog) -> None:
        self.catalog = catalog

    def validate(self, template: TemplateSpec, result: ComposerResult) -> list[ValidationIssue]:
        prompt_spec = result.prompt_spec
        text = result.prompt_text
        issues: list[ValidationIssue] = []

        if not prompt_spec.goal.strip():
            issues.append(
                ValidationIssue(
                    code="missing_goal",
                    severity="error",
                    message="Goal section is missing confirmed content.",
                    section="Goal",
                    slot="goal",
                )
            )

        required_sections = {
            "Context / Inputs": prompt_spec.context_items or prompt_spec.input_items,
            "Constraints": prompt_spec.constraint_items,
            "Deliverables": prompt_spec.deliverables,
            "Acceptance Criteria": prompt_spec.acceptance_criteria,
            "Output Format": [prompt_spec.output_format],
        }
        for section, items in required_sections.items():
            if not items:
                issues.append(
                    ValidationIssue(
                        code="missing_section",
                        severity="error",
                        message=f"{section} section is empty.",
                        section=section,
                    )
                )

        normalized_text = normalize_for_match(text)
        for slot in template.required_slots:
            value = prompt_spec.facts_snapshot.get(slot, "").strip()
            if not value:
                issues.append(
                    ValidationIssue(
                        code="missing_required_slot",
                        severity="error",
                        message=f"Required slot `{slot}` has not been confirmed.",
                        slot=slot,
                    )
                )
                continue
            if normalize_for_match(value) not in normalized_text:
                section = self.catalog.slots.get(slot).section if slot in self.catalog.slots else None
                issues.append(
                    ValidationIssue(
                        code="fact_not_preserved",
                        severity="error",
                        message=f"Confirmed fact `{slot}` is not preserved in the composed prompt.",
                        section=section,
                        slot=slot,
                    )
                )

        result.issues = issues
        return issues
