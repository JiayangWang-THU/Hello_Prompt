from __future__ import annotations

from hpa.domain import ChoiceOption, ChoicePrompt, SessionState, TemplateCatalog, TemplateSpec

from .contracts import LLMEnhancer


class ModeResolverService:
    def __init__(
        self,
        catalog: TemplateCatalog,
        llm: LLMEnhancer | None = None,
        enable_mode_router: bool = False,
    ) -> None:
        self.catalog = catalog
        self.llm = llm
        self.enable_mode_router = enable_mode_router

    def set_mode(self, state: SessionState, category: str, subtype: str) -> TemplateSpec:
        mode_key = f"{category.upper()}/{subtype.upper()}"
        template = self.catalog.get_template(mode_key)
        if template is None:
            raise ValueError(f"不支持的模式：{mode_key}")
        state.category = template.category
        state.subtype = template.subtype
        state.last_asked_slot = None
        state.suggestions.clear()
        state.pending_questions.clear()
        return template

    def current_template(self, state: SessionState) -> TemplateSpec | None:
        mode_key = state.mode_key()
        if not mode_key:
            return None
        return self.catalog.get_template(mode_key)

    def propose_mode_choice(self, state: SessionState, user_text: str) -> ChoicePrompt:
        if state.mode_key():
            raise ValueError("当前 session 已经有 mode。")

        if self.enable_mode_router and self.llm is not None:
            choice = self.llm.propose_mode_choice(self.catalog, user_text)
            if choice is not None and choice.options:
                return choice

        ordered = list(self.catalog.templates.values())
        options = [
            ChoiceOption(
                key=str(idx),
                label=f"{template.mode_key}  ({template.label})",
                value=template.mode_key,
                rationale=template.description or template.label,
            )
            for idx, template in enumerate(ordered, 1)
        ]
        return ChoicePrompt(
            kind="mode_select",
            title="请选择最接近你当前任务的 mode",
            question="先确定 prompt 的主类型。输入数字选择；如判断不准，也可以继续补充一句需求。",
            options=options,
            allow_manual_text=True,
            manual_text_hint="例如：这个任务更像在现有项目上加功能。",
            source_user_text=user_text,
        )
