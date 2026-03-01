from __future__ import annotations

from typing import Protocol

from hpa.domain import (
    ChoicePrompt,
    PromptSpec,
    SharedPromptDocument,
    SessionState,
    TemplateCatalog,
    TemplateSpec,
    ValidationIssue,
)


class LLMEnhancer(Protocol):
    """Boundary for optional LLM-powered enhancements."""

    def propose_mode_choice(self, catalog: TemplateCatalog, user_text: str) -> ChoicePrompt | None:
        ...

    def extract_slots(
        self,
        catalog: TemplateCatalog,
        template: TemplateSpec,
        state: SessionState,
        user_text: str,
    ) -> dict[str, str]:
        ...

    def propose_slot_choice(
        self,
        catalog: TemplateCatalog,
        template: TemplateSpec,
        state: SessionState,
        slot: str,
        recent_user_text: str,
    ) -> ChoicePrompt | None:
        ...

    def refine_prompt(
        self,
        template: TemplateSpec,
        prompt_spec: PromptSpec,
        prompt_text: str,
    ) -> str:
        ...

    def repair_prompt(
        self,
        template: TemplateSpec,
        prompt_spec: PromptSpec,
        prompt_text: str,
        issues: list[ValidationIssue],
    ) -> str:
        ...

    def propose_document_revision(
        self,
        template: TemplateSpec,
        document: SharedPromptDocument,
        section_key: str,
        instruction: str,
    ) -> ChoicePrompt | None:
        ...


class CapabilityProvider(Protocol):
    """Lightweight plugin point for optional post-structure assistance."""

    def suggest(
        self,
        stage: str,
        template: TemplateSpec,
        state: SessionState,
        prompt_spec: PromptSpec | None = None,
    ) -> list[Suggestion]:
        ...
