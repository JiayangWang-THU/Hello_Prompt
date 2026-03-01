from __future__ import annotations

from hpa.domain import ComposerResult, TemplateSpec, ValidationIssue

from .contracts import LLMEnhancer


class RepairService:
    def __init__(
        self,
        llm: LLMEnhancer | None = None,
        enable_repair: bool = False,
    ) -> None:
        self.llm = llm
        self.enable_repair = enable_repair

    def repair(
        self,
        template: TemplateSpec,
        result: ComposerResult,
        fallback_text: str,
    ) -> ComposerResult:
        if not result.issues:
            return result

        repaired_text = fallback_text
        if self.enable_repair and self.llm is not None:
            candidate = self.llm.repair_prompt(template, result.prompt_spec, result.prompt_text, result.issues)
            if candidate.strip():
                repaired_text = candidate

        return ComposerResult(
            prompt_spec=result.prompt_spec,
            prompt_text=repaired_text,
            document=result.document,
            issues=list(result.issues),
            repaired=True,
        )
