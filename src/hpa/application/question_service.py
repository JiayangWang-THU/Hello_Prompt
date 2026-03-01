from __future__ import annotations

from hpa.domain import ChoiceOption, ChoicePrompt, SessionState, TemplateCatalog, TemplateSpec

from .contracts import LLMEnhancer


class QuestionPlanningService:
    def __init__(
        self,
        catalog: TemplateCatalog,
        llm: LLMEnhancer,
        max_questions_per_turn: int = 1,
    ) -> None:
        self.catalog = catalog
        self.llm = llm
        self.max_questions_per_turn = max_questions_per_turn

    def missing_slots(self, state: SessionState, template: TemplateSpec) -> list[str]:
        missing = [slot for slot in template.required_slots if not state.confirmed_slots.get(slot, "").strip()]
        missing.sort(
            key=lambda slot: self.catalog.slot_priority.index(slot)
            if slot in self.catalog.slot_priority
            else 999
        )
        return missing

    def plan_next_choice(self, state: SessionState, template: TemplateSpec) -> ChoicePrompt | None:
        missing = self.missing_slots(state, template)
        if not missing:
            return None

        slot = missing[0]
        choice = self.llm.propose_slot_choice(
            self.catalog,
            template,
            state,
            slot=slot,
            recent_user_text=self._latest_user_text(state),
        )
        if choice is not None and choice.options:
            return choice

        slot_def = self.catalog.slots.get(slot)
        return ChoicePrompt(
            kind="slot_select",
            title=f"请补全 {slot_def.label if slot_def else slot}",
            question=slot_def.question if slot_def else f"请补充：{slot}",
            options=[
                ChoiceOption(
                    key="1",
                    label="我自己补充一段文本",
                    value="__manual__",
                    rationale="当前没有高质量候选答案。",
                )
            ],
            slot=slot,
            allow_manual_text=True,
            manual_text_hint="直接输入一小段文字即可。",
        )

    def _latest_user_text(self, state: SessionState) -> str:
        for turn in reversed(state.history):
            if turn.role == "user" and turn.content.strip():
                return turn.content.strip()
        return (state.seed_intent or "").strip()
