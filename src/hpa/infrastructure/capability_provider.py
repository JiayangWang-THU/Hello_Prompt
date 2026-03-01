from __future__ import annotations

from hpa.domain import PromptSpec, SessionState, Suggestion, TemplateSpec


class DisabledCapabilityProvider:
    """Reserved plugin point. Disabled by default for MVP simplicity."""

    def suggest(
        self,
        stage: str,
        template: TemplateSpec,
        state: SessionState,
        prompt_spec: PromptSpec | None = None,
    ) -> list[Suggestion]:
        return []
