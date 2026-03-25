from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hpa.domain import ChoicePrompt, ComposerResult, SessionState, TemplateCatalog, TurnRecord

from .composition_service import PromptCompositionService
from .mode_service import ModeResolverService
from .question_service import ConvergencePlanningService
from .repair_service import RepairService
from .session_service import SessionService
from .slot_service import SlotFillingService
from .validation_service import ValidationService


@dataclass
class InteractionResult:
    text: str
    done: bool = False
    composer_result: ComposerResult | None = None


class ClarificationService:
    """LLM-driven demand convergence workflow with iterative planning."""

    def __init__(
        self,
        catalog: TemplateCatalog,
        mode_service: ModeResolverService,
        slot_service: SlotFillingService,
        question_service: ConvergencePlanningService,
        composition_service: PromptCompositionService,
        validation_service: ValidationService,
        repair_service: RepairService,
        session_service: SessionService,
        llm,
    ) -> None:
        self.catalog = catalog
        self.mode_service = mode_service
        self.slot_service = slot_service
        self.question_service = question_service
        self.composition_service = composition_service
        self.validation_service = validation_service
        self.repair_service = repair_service
        self.session_service = session_service
        self.llm = llm
        self.state = SessionState()

    def reset(self) -> InteractionResult:
        self.state = self.session_service.reset()
        intro = (
            "已重置。\n"
            "直接描述你的任务即可。我会先猜测你更接近的任务方向，再通过 top-k 建议逐轮收敛你的真实需求。"
        )
        return InteractionResult(text=intro, done=False)

    def mode_menu_text(self) -> str:
        return self.catalog.mode_menu_text()

    def set_mode(self, category: str, subtype: str) -> InteractionResult:
        template = self.mode_service.set_mode(self.state, category, subtype)
        if self.state.seed_intent:
            self.slot_service.apply_free_text(self.state, template, self.state.seed_intent)
        return self._advance_after_update(
            prefix=f"模式已设定为 {template.mode_key}。",
        )

    def show_state(self) -> InteractionResult:
        template = self.mode_service.current_template(self.state)
        return InteractionResult(text=self.session_service.show_state(self.state, template), done=False)

    def show_document(self) -> InteractionResult:
        return InteractionResult(text=self.session_service.show_document(self.state), done=False)

    def clear_slot(self, slot: str) -> InteractionResult:
        return InteractionResult(text=self.session_service.clear_slot(self.state, slot), done=False)

    def export(self) -> InteractionResult:
        return InteractionResult(text=self.session_service.export(self.state, self.state.latest_result), done=False)

    def compose_draft(self) -> InteractionResult:
        template = self.mode_service.current_template(self.state)
        if template is None:
            return InteractionResult(text="请先描述你的任务，完成 mode 选择。", done=False)
        result = self.composition_service.compose(self.state, template)
        self.state.latest_result = result
        self.state.latest_document = result.document
        self.state.draft_text = result.prompt_text
        issues = self.validation_service.validate(template, result)
        self.state.latest_validation_issues = issues
        return InteractionResult(
            text="当前共享文档草稿如下：\n\n" + result.prompt_text,
            done=not result.prompt_spec.missing_info,
            composer_result=result,
        )

    def lint(self) -> InteractionResult:
        template = self.mode_service.current_template(self.state)
        if template is None:
            return InteractionResult(text="请先描述你的任务，完成 mode 选择。", done=False)
        result = self.state.latest_result or self.composition_service.compose(self.state, template)
        issues = self.validation_service.validate(template, result)
        self.state.latest_result = result
        self.state.latest_document = result.document
        self.state.latest_validation_issues = issues
        if not issues:
            return InteractionResult(text="Lint 通过：未发现结构性问题。", done=False, composer_result=result)
        lines = ["Lint 发现以下问题："]
        lines.extend(f"- [{issue.severity}] {issue.code}: {issue.message}" for issue in issues)
        return InteractionResult(text="\n".join(lines), done=False, composer_result=result)

    def repair(self) -> InteractionResult:
        template = self.mode_service.current_template(self.state)
        if template is None:
            return InteractionResult(text="请先描述你的任务，完成 mode 选择。", done=False)
        current = self.state.latest_result or self.composition_service.compose(self.state, template)
        fallback = self.composition_service.render_prompt(current.prompt_spec)
        if not current.issues:
            current.issues = self.validation_service.validate(template, current)
        repaired = self.repair_service.repair(template, current, fallback)
        repaired.issues = self.validation_service.validate(template, repaired)
        self.state.latest_result = repaired
        self.state.latest_document = repaired.document
        self.state.draft_text = repaired.prompt_text
        self.state.latest_validation_issues = repaired.issues
        text = "Repair 结果：\n\n" + repaired.prompt_text
        if repaired.issues:
            text += "\n\n仍存在问题：\n" + "\n".join(
                f"- [{issue.severity}] {issue.code}: {issue.message}" for issue in repaired.issues
            )
        return InteractionResult(text=text, done=not repaired.issues, composer_result=repaired)

    def revise_document(self, section_key: str, instruction: str | None = None) -> InteractionResult:
        template = self.mode_service.current_template(self.state)
        if template is None:
            return InteractionResult(text="请先完成 mode 选择后再改写文档。", done=False)
        if self.state.latest_document is None:
            composed = self.composition_service.compose(self.state, template)
            self.state.latest_result = composed
            self.state.latest_document = composed.document
            self.state.draft_text = composed.prompt_text
        document = self.state.latest_document
        assert document is not None
        prompt = self.llm.propose_document_revision(
            template,
            document,
            section_key,
            instruction or "improve clarity while preserving facts",
        )
        if prompt is None:
            return InteractionResult(text="当前没能生成 section 改写建议。请换个 section，或先补充更多真实意图。", done=False)
        self.state.pending_choice = prompt
        return InteractionResult(text=self._render_choice_prompt(prompt), done=False)

    def handle_user_message(self, user_text: str) -> InteractionResult:
        self.state.turn += 1
        self.state.history.append(TurnRecord(role="user", content=user_text))

        if self._looks_like_choice_selection(user_text) and self.state.pending_choice is not None:
            return self._handle_choice_selection(user_text)

        if self.state.pending_choice is not None and self.state.pending_choice.kind == "doc_revision":
            if self.state.latest_document is None:
                return InteractionResult(text="当前没有共享文档可供改写。", done=False)
            updated = self.composition_service.apply_document_section(
                self.state.latest_document,
                self.state.pending_choice.section_key or "",
                user_text,
            )
            self.state.pending_choice = None
            self.state.latest_document = updated
            self.state.draft_text = self.composition_service.render_document(updated)
            if self.state.latest_result is not None:
                self.state.latest_result = self.state.latest_result.model_copy(
                    update={"prompt_text": self.state.draft_text, "document": updated}
                )
            return InteractionResult(
                text="已按你的文本直接更新该 section：\n\n" + self.state.draft_text,
                done=False,
                composer_result=self.state.latest_result,
            )

        if not self.state.mode_key():
            self.state.seed_intent = user_text
            choice = self.mode_service.propose_mode_choice(self.state, user_text)
            self.state.pending_choice = choice
            response = InteractionResult(text=self._render_choice_prompt(choice), done=False)
            self.state.history.append(TurnRecord(role="assistant", content=response.text))
            return response

        template = self.mode_service.current_template(self.state)
        if template is None:
            choice = self.mode_service.propose_mode_choice(self.state, user_text)
            self.state.pending_choice = choice
            return InteractionResult(text=self._render_choice_prompt(choice), done=False)

        focus_slot = (
            self.state.pending_choice.slot
            if self.state.pending_choice and self.state.pending_choice.kind == "hypothesis_select"
            else None
        )
        self.slot_service.apply_free_text(self.state, template, user_text, focus_slot=focus_slot)
        self.state.pending_choice = None
        response = self._advance_after_update()
        self.state.history.append(TurnRecord(role="assistant", content=response.text))
        return response

    def _advance_after_update(self, prefix: str | None = None) -> InteractionResult:
        template = self.mode_service.current_template(self.state)
        if template is None:
            return InteractionResult(text="请先完成 mode 选择。", done=False)

        next_choice = self.question_service.plan_next_choice(self.state, template)
        if next_choice is not None:
            self.state.pending_choice = next_choice
            text = self._render_choice_prompt(next_choice)
            if prefix:
                text = prefix + "\n" + text
            return InteractionResult(text=text, done=False)

        self.state.pending_choice = None
        composed = self.composition_service.compose(self.state, template)
        self.state.latest_result = composed
        self.state.latest_document = composed.document
        self.state.draft_text = composed.prompt_text
        issues = self.validation_service.validate(template, composed)
        self.state.latest_validation_issues = issues

        text_prefix = f"{prefix}\n" if prefix else ""
        response_text = text_prefix + "当前信息已经足够稳定，下面是收敛后的共享 prompt 文档：\n\n" + composed.prompt_text
        if issues:
            response_text += "\n\nLint 提示：\n" + "\n".join(
                f"- [{issue.severity}] {issue.code}: {issue.message}" for issue in issues
            )
            response_text += "\n可使用 /repair 或 /revise <section> 继续调整。"
        return InteractionResult(
            text=response_text,
            done=not issues,
            composer_result=composed,
        )

    def _handle_choice_selection(self, user_text: str) -> InteractionResult:
        assert self.state.pending_choice is not None
        pending = self.state.pending_choice
        index = int(user_text.strip()) - 1
        if index < 0 or index >= len(pending.options):
            return InteractionResult(text="无效选择，请输入当前题目的数字编号。", done=False)
        option = pending.options[index]
        self.state.pending_choice = None

        if pending.kind == "mode_select":
            mode_key = option.value
            category, subtype = mode_key.split("/", maxsplit=1)
            return self.set_mode(category, subtype)

        if pending.kind == "hypothesis_select":
            if option.value == "__manual__":
                self.state.pending_choice = pending
                hint = pending.manual_text_hint or "请直接输入一小段文字。"
                return InteractionResult(text=f"请直接修正系统的猜测。\n{hint}", done=False)
            self.slot_service.apply_choice_selection(self.state, pending.slot or "", option.value)
            return self._advance_after_update(prefix=f"已采用这条收敛建议：{option.label}")

        if pending.kind == "doc_revision":
            if self.state.latest_document is None:
                return InteractionResult(text="当前没有共享文档可供改写。", done=False)
            updated = self.composition_service.apply_document_section(
                self.state.latest_document,
                pending.section_key or "",
                option.value,
            )
            self.state.latest_document = updated
            self.state.draft_text = self.composition_service.render_document(updated)
            if self.state.latest_result is not None:
                self.state.latest_result = self.state.latest_result.model_copy(
                    update={"prompt_text": self.state.draft_text, "document": updated}
                )
            return InteractionResult(
                text="已更新共享 prompt 文档：\n\n" + self.state.draft_text,
                done=False,
                composer_result=self.state.latest_result,
            )

        return InteractionResult(text="当前选择题类型不受支持。", done=False)

    def _looks_like_choice_selection(self, user_text: str) -> bool:
        text = user_text.strip()
        return text.isdigit()

    def _render_choice_prompt(self, choice: ChoicePrompt) -> str:
        lines = [choice.title, choice.question]
        if choice.planning_note:
            lines.append(f"推进策略：{choice.planning_note}")
        for idx, option in enumerate(choice.options, 1):
            line = f"{idx}. {option.label}"
            if option.rationale:
                line += f"  ({option.rationale})"
            lines.append(line)
        if choice.allow_manual_text:
            hint = choice.manual_text_hint or "如果这些选项都不合适，可以直接输入一小段文字。"
            lines.append(f"直接输入文本也可以：{hint}")
        return "\n".join(lines)

    def snapshot(self) -> dict[str, Any]:
        template = self.mode_service.current_template(self.state)
        missing_slots = self.question_service.missing_slots(self.state, template) if template else []
        latest_document = self.state.latest_document
        pending_choice = self.state.pending_choice
        latest_result = self.state.latest_result
        return {
            "mode_key": self.state.mode_key(),
            "template_label": template.label if template else None,
            "confirmed_slots": dict(self.state.confirmed_slots),
            "current_focus": self.state.current_focus,
            "missing_slots": missing_slots,
            "pending_choice": self._serialize_choice_prompt(pending_choice),
            "document": {
                "mode_key": latest_document.mode_key,
                "version": latest_document.version,
                "sections": [
                    {
                        "key": section.key,
                        "title": section.title,
                        "content": section.content,
                    }
                    for section in latest_document.sections
                ],
            }
            if latest_document
            else None,
            "draft_text": self.state.draft_text,
            "history": [
                {
                    "role": turn.role,
                    "content": turn.content,
                }
                for turn in self.state.history
            ],
            "suggestions": [
                {
                    "kind": suggestion.kind,
                    "source": suggestion.source,
                    "message": suggestion.message,
                    "slot": suggestion.slot,
                    "proposed_value": suggestion.proposed_value,
                    "rationale": suggestion.rationale,
                }
                for suggestion in self.state.suggestions
            ],
            "validation_issues": [
                issue.model_dump(mode="json") for issue in self.state.latest_validation_issues
            ],
            "latest_prompt_spec": latest_result.prompt_spec.model_dump(mode="json") if latest_result else None,
        }

    def _serialize_choice_prompt(self, choice: ChoicePrompt | None) -> dict[str, Any] | None:
        if choice is None:
            return None
        return {
            "kind": choice.kind,
            "title": choice.title,
            "question": choice.question,
            "slot": choice.slot,
            "section_key": choice.section_key,
            "focus_label": choice.focus_label,
            "planning_note": choice.planning_note,
            "allow_manual_text": choice.allow_manual_text,
            "manual_text_hint": choice.manual_text_hint,
            "options": [
                {
                    "key": option.key,
                    "label": option.label,
                    "value": option.value,
                    "rationale": option.rationale,
                }
                for option in choice.options
            ],
        }
