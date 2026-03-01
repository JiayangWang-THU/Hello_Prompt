from __future__ import annotations

from hpa.application.composition_service import PromptCompositionService
from hpa.config import TemplatesConfig
from hpa.infrastructure.capability_provider import DisabledCapabilityProvider


def compose_prompt(state, cfg: TemplatesConfig) -> str:
    mode_key = state.mode_key()
    if not mode_key:
        return ""
    template = cfg.catalog.get_template(mode_key)
    if template is None:
        return ""
    service = PromptCompositionService(
        catalog=cfg.catalog,
        llm=None,
        capability_provider=DisabledCapabilityProvider(),
        enable_refinement=False,
    )
    return service.compose(state, template).prompt_text
