from __future__ import annotations

from hpa.domain import ChoiceOption, ChoicePrompt, SessionState, TemplateCatalog, TemplateSpec

from .contracts import LLMEnhancer


class ConvergencePlanningService:
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
            state.current_focus = None
            return None

        slot = missing[0]
        state.current_focus = slot
        choice = self.llm.propose_hypothesis_choice(
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
            kind="hypothesis_select",
            title=f"我先帮你收敛这一轮最关键的一步：{slot_def.label if slot_def else slot}",
            question=(
                f"基于你刚才的描述，我还不能稳定判断“{slot_def.label if slot_def else slot}”。"
                " 你可以直接输入你的表述，或者让我继续根据更多上下文猜。"
            ),
            options=[
                ChoiceOption(
                    key="1",
                    label="我直接补充我的真实想法",
                    value="__manual__",
                    rationale="当前没有足够稳的候选猜测。",
                )
            ],
            slot=slot,
            focus_label=slot_def.label if slot_def else slot,
            planning_note="系统当前只推进最值得确认的一步，而不是让你一次性填完整张表。",
            allow_manual_text=True,
            manual_text_hint="直接输入一小段文字，修正系统对你意图的猜测。",
        )

    def _latest_user_text(self, state: SessionState) -> str:
        for turn in reversed(state.history):
            if turn.role == "user" and turn.content.strip():
                return turn.content.strip()
        return (state.seed_intent or "").strip()


QuestionPlanningService = ConvergencePlanningService
