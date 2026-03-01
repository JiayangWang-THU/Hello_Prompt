from __future__ import annotations

from hpa.domain import ComposerResult, SessionState, Suggestion, TemplateCatalog, TemplateSpec


class SessionService:
    def __init__(self, catalog: TemplateCatalog, exporter) -> None:
        self.catalog = catalog
        self.exporter = exporter

    def reset(self) -> SessionState:
        return SessionState()

    def show_state(self, state: SessionState, template: TemplateSpec | None) -> str:
        lines: list[str] = []
        lines.append(f"当前 mode: {state.mode_key() or '(未选择)'}")
        if template is None:
            if state.pending_choice is not None:
                lines.append("当前等待中的选择题：")
                lines.extend(self._render_choice_lines(state))
            else:
                lines.append("请先描述你的任务，系统会先给出推荐 mode 选择。")
            return "\n".join(lines)

        missing = [slot for slot in template.required_slots if not state.confirmed_slots.get(slot, "").strip()]
        filled = [slot for slot in template.required_slots if slot not in missing]
        lines.append("已填 slots:")
        if filled:
            lines.extend(f"- {slot}: {state.confirmed_slots.get(slot, '')}" for slot in filled)
        else:
            lines.append("- (none)")
        lines.append("缺失 slots:")
        if missing:
            lines.extend(f"- {slot}" for slot in missing)
        else:
            lines.append("- (none)")
        lines.append("建议项:")
        if state.suggestions:
            lines.extend(f"- [{s.source}/{s.kind}] {s.message}" for s in state.suggestions)
        else:
            lines.append("- (none)")
        if state.pending_choice is not None:
            lines.append("当前等待中的选择题:")
            lines.extend(self._render_choice_lines(state))
        return "\n".join(lines)

    def clear_slot(self, state: SessionState, slot: str) -> str:
        normalized = self.catalog.normalize_key(slot)
        if normalized in state.confirmed_slots:
            state.confirmed_slots.pop(normalized, None)
            if state.last_asked_slot == normalized:
                state.last_asked_slot = None
            return f"已清除槽位：{normalized}"
        return f"未找到槽位：{normalized}"

    def export(self, state: SessionState, result: ComposerResult | None) -> str:
        path = self.exporter.export_session(state, result)
        return f"已导出：{path}"

    def replace_suggestions(self, state: SessionState, suggestions: list[Suggestion]) -> None:
        state.suggestions = suggestions

    def show_document(self, state: SessionState) -> str:
        if state.latest_document is None:
            return "当前还没有共享 prompt 文档。请先补充信息，或使用 /draft 生成草稿。"
        lines = [f"共享 prompt 文档（v{state.latest_document.version}）:"]
        for section in state.latest_document.sections:
            lines.append(f"[{section.key}] {section.title}")
            lines.append(section.content)
            lines.append("")
        lines.append("可使用 /revise <section> [指令] 对某一段进行定向改写。")
        return "\n".join(lines).rstrip()

    def _render_choice_lines(self, state: SessionState) -> list[str]:
        if state.pending_choice is None:
            return ["- (none)"]
        lines = [f"- {state.pending_choice.title}", f"  {state.pending_choice.question}"]
        for idx, option in enumerate(state.pending_choice.options, 1):
            suffix = f"  ({option.rationale})" if option.rationale else ""
            lines.append(f"  {idx}. {option.label}{suffix}")
        if state.pending_choice.allow_manual_text:
            hint = state.pending_choice.manual_text_hint or "直接输入一小段文字。"
            lines.append(f"  或直接输入文本：{hint}")
        return lines
