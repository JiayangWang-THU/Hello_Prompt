from __future__ import annotations

from dataclasses import dataclass

from hpa.domain import SessionState, TemplateCatalog, TemplateSpec

from .contracts import LLMEnhancer


@dataclass
class SlotUpdateResult:
    updated_slots: list[str]
    updated_by_rule: list[str]
    updated_by_llm: list[str]


class SlotFillingService:
    def __init__(
        self,
        catalog: TemplateCatalog,
        llm: LLMEnhancer,
        fill_only_empty_slots: bool = True,
    ) -> None:
        self.catalog = catalog
        self.llm = llm
        self.fill_only_empty_slots = fill_only_empty_slots

    def apply_free_text(
        self,
        state: SessionState,
        template: TemplateSpec,
        user_text: str,
        focus_slot: str | None = None,
    ) -> SlotUpdateResult:
        updated_by_llm: list[str] = []
        direct_updates: list[str] = []

        if focus_slot:
            normalized_focus = self.catalog.normalize_key(focus_slot)
            current_value = state.confirmed_slots.get(normalized_focus, "").strip()
            if not current_value or not self.fill_only_empty_slots:
                state.confirmed_slots[normalized_focus] = user_text.strip()
                direct_updates.append(normalized_focus)

        llm_updates = self.llm.extract_slots(self.catalog, template, state, user_text)
        for key, value in llm_updates.items():
            normalized = self.catalog.normalize_key(key)
            if normalized in direct_updates:
                continue
            if self.fill_only_empty_slots and state.confirmed_slots.get(normalized, "").strip():
                continue
            if value.strip():
                state.confirmed_slots[normalized] = value.strip()
                updated_by_llm.append(normalized)

        updated_slots = list(dict.fromkeys(direct_updates + updated_by_llm))
        return SlotUpdateResult(
            updated_slots=updated_slots,
            updated_by_rule=direct_updates,
            updated_by_llm=updated_by_llm,
        )

    def apply_choice_selection(self, state: SessionState, slot: str, value: str) -> SlotUpdateResult:
        normalized = self.catalog.normalize_key(slot)
        if not value.strip():
            return SlotUpdateResult(updated_slots=[], updated_by_rule=[], updated_by_llm=[])
        if self.fill_only_empty_slots and state.confirmed_slots.get(normalized, "").strip():
            return SlotUpdateResult(updated_slots=[], updated_by_rule=[], updated_by_llm=[])
        state.confirmed_slots[normalized] = value.strip()
        return SlotUpdateResult(
            updated_slots=[normalized],
            updated_by_rule=[normalized],
            updated_by_llm=[],
        )
