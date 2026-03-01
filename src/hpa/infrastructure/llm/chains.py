from __future__ import annotations

import sys
import traceback
from typing import Any

from hpa.domain import (
    ChoiceOption,
    ChoicePrompt,
    PromptSpec,
    SessionState,
    SharedPromptDocument,
    TemplateCatalog,
    TemplateSpec,
    ValidationIssue,
)
from hpa.infrastructure.llm.parsers import (
    DocRevisionPayload,
    ModeRoutingPayload,
    PromptTextPayload,
    SlotChoicePayload,
    SlotExtractionPayload,
    parse_pydantic_json,
    parse_slot_choice_payload,
)

from .prompts import (
    DOC_REVISION_SYSTEM,
    MODE_ROUTING_SYSTEM,
    REFINE_SYSTEM,
    REPAIR_SYSTEM,
    SLOT_CHOICE_SYSTEM,
    SLOT_CHOICE_TEXT_FALLBACK_SYSTEM,
    SLOT_EXTRACTION_SYSTEM,
)


def _ensure_langchain() -> tuple[Any, Any, Any]:
    try:
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.runnables import RunnableLambda
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "LangChain 依赖未安装。请安装 langchain-core 和 langchain-openai 后再启用 agent。"
        ) from exc
    return ChatPromptTemplate, StrOutputParser, RunnableLambda


class LangChainLLMEnhancer:
    """LLM enhancer built on LangChain Runnable pipelines."""

    def __init__(self, model, strict_json_only: bool = True, debug: bool = False) -> None:
        self.model = model
        self.strict_json_only = strict_json_only
        self.debug = debug
        (
            self._slot_chain,
            self._mode_chain,
            self._slot_choice_chain,
            self._slot_choice_text_chain,
            self._refine_chain,
            self._repair_chain,
            self._doc_revision_chain,
        ) = self._build_chains()

    def _build_chains(self):
        ChatPromptTemplate, StrOutputParser, RunnableLambda = _ensure_langchain()

        slot_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SLOT_EXTRACTION_SYSTEM),
                (
                    "user",
                    "mode_key: {mode_key}\nallowed_slots: {allowed_slots}\ncurrent_facts: {current_facts}\nuser_message: {user_message}",
                ),
            ]
        )
        mode_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", MODE_ROUTING_SYSTEM),
                ("user", "available_modes: {available_modes}\nuser_message: {user_message}"),
            ]
        )
        slot_choice_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SLOT_CHOICE_SYSTEM),
                (
                    "user",
                    "mode_key: {mode_key}\nslot_key: {slot_key}\nslot_label: {slot_label}\nslot_question: {slot_question}\nslot_description: {slot_description}\nrecent_user_message: {recent_user_message}\nconfirmed_facts: {confirmed_facts}",
                ),
            ]
        )
        slot_choice_text_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SLOT_CHOICE_TEXT_FALLBACK_SYSTEM),
                (
                    "user",
                    "mode_key: {mode_key}\nslot_key: {slot_key}\nslot_label: {slot_label}\nslot_question: {slot_question}\nslot_description: {slot_description}\nrecent_user_message: {recent_user_message}\nconfirmed_facts: {confirmed_facts}",
                ),
            ]
        )
        refine_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", REFINE_SYSTEM),
                (
                    "user",
                    "confirmed_facts: {confirmed_facts}\nmode_key: {mode_key}\nprompt_draft:\n{prompt_text}",
                ),
            ]
        )
        repair_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", REPAIR_SYSTEM),
                (
                    "user",
                    "mode_key: {mode_key}\nconfirmed_facts: {confirmed_facts}\nissues: {issues}\nprompt_draft:\n{prompt_text}",
                ),
            ]
        )
        doc_revision_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", DOC_REVISION_SYSTEM),
                (
                    "user",
                    "mode_key: {mode_key}\nsection_key: {section_key}\nsection_text:\n{section_text}\ninstruction: {instruction}\nconfirmed_facts: {confirmed_facts}",
                ),
            ]
        )

        slot_chain = slot_prompt | self.model | StrOutputParser() | RunnableLambda(
            lambda text: parse_pydantic_json(SlotExtractionPayload, text, self.strict_json_only)
        )
        mode_chain = mode_prompt | self.model | StrOutputParser() | RunnableLambda(
            lambda text: parse_pydantic_json(ModeRoutingPayload, text, self.strict_json_only)
        )
        slot_choice_chain = slot_choice_prompt | self.model | StrOutputParser()
        slot_choice_text_chain = slot_choice_text_prompt | self.model | StrOutputParser()
        refine_chain = refine_prompt | self.model | StrOutputParser() | RunnableLambda(
            lambda text: parse_pydantic_json(PromptTextPayload, text, self.strict_json_only)
        )
        repair_chain = repair_prompt | self.model | StrOutputParser() | RunnableLambda(
            lambda text: parse_pydantic_json(PromptTextPayload, text, self.strict_json_only)
        )
        doc_revision_chain = doc_revision_prompt | self.model | StrOutputParser() | RunnableLambda(
            lambda text: parse_pydantic_json(DocRevisionPayload, text, self.strict_json_only)
        )
        return (
            slot_chain,
            mode_chain,
            slot_choice_chain,
            slot_choice_text_chain,
            refine_chain,
            repair_chain,
            doc_revision_chain,
        )

    def propose_mode_choice(self, catalog: TemplateCatalog, user_text: str) -> ChoicePrompt | None:
        try:
            payload = self._mode_chain.invoke(
                {
                    "available_modes": sorted(catalog.templates.keys()),
                    "user_message": user_text,
                }
            )
        except Exception:  # noqa: BLE001
            payload = None
        recommended = payload.recommended_mode if payload else None
        ordered_templates: list[TemplateSpec] = []
        if recommended and catalog.get_template(recommended):
            ordered_templates.append(catalog.get_template(recommended))
        for template in catalog.templates.values():
            if template not in ordered_templates:
                ordered_templates.append(template)
        options = [
            ChoiceOption(
                key=str(idx),
                label=f"{template.mode_key}  ({template.label})",
                value=template.mode_key,
                rationale=(payload.reason if template.mode_key == recommended else template.description or template.label)
                if payload
                else (template.description or template.label),
            )
            for idx, template in enumerate(ordered_templates, 1)
        ]
        return ChoicePrompt(
            kind="mode_select",
            title=payload.title if payload else "请选择一个 mode",
            question=payload.question if payload else "输入数字选择最接近的任务类型。",
            options=options,
            allow_manual_text=payload.allow_manual_text if payload else True,
            manual_text_hint="如果不确定，可以再补充一句你的任务目标。",
            source_user_text=user_text,
        )

    def extract_slots(
        self,
        catalog: TemplateCatalog,
        template: TemplateSpec,
        state: SessionState,
        user_text: str,
    ) -> dict[str, str]:
        try:
            payload = self._slot_chain.invoke(
                {
                    "mode_key": template.mode_key,
                    "allowed_slots": sorted(catalog.slots.keys()),
                    "current_facts": state.confirmed_slots,
                    "user_message": user_text,
                }
            )
        except Exception:  # noqa: BLE001
            payload = None
        if payload is None:
            return {}
        results: dict[str, str] = {}
        for raw_key, raw_value in payload.updates.items():
            key = catalog.normalize_key(raw_key)
            value = str(raw_value).strip()
            if key in catalog.slots and value:
                results[key] = value
        return results

    def propose_slot_choice(
        self,
        catalog: TemplateCatalog,
        template: TemplateSpec,
        state: SessionState,
        slot: str,
        recent_user_text: str,
    ) -> ChoicePrompt | None:
        slot_key = catalog.normalize_key(slot)
        slot_def = catalog.slots.get(slot_key)
        structured_raw = ""
        payload: SlotChoicePayload | None = None

        try:
            structured_raw = self._slot_choice_chain.invoke(
                {
                    "mode_key": template.mode_key,
                    "slot_key": slot_key,
                    "slot_label": slot_def.label if slot_def else slot_key,
                    "slot_question": slot_def.question if slot_def else slot_key,
                    "slot_description": slot_def.description if slot_def else "",
                    "recent_user_message": recent_user_text,
                    "confirmed_facts": state.confirmed_slots,
                }
            )
            payload = parse_slot_choice_payload(structured_raw, self.strict_json_only, default_slot=slot_key)
        except Exception:  # noqa: BLE001
            self._debug("slot-choice structured generation failed", exc_info=True)

        if payload is None:
            if structured_raw:
                self._debug(f"slot-choice structured raw response rejected: {structured_raw}")
            payload = self._fallback_slot_choice_payload(
                template=template,
                state=state,
                slot_key=slot_key,
                slot_label=slot_def.label if slot_def else slot_key,
                slot_question=slot_def.question if slot_def else slot_key,
                slot_description=slot_def.description if slot_def else "",
                recent_user_text=recent_user_text,
            )

        if payload is None or not payload.options:
            return None

        return ChoicePrompt(
            kind="slot_select",
            title=payload.title or f"请补全 {slot_def.label if slot_def else slot_key}",
            question=payload.question or (slot_def.question if slot_def else f"请补充：{slot_key}"),
            options=[
                ChoiceOption(
                    key=str(idx),
                    label=option.label,
                    value=option.value,
                    rationale=option.rationale,
                )
                for idx, option in enumerate(payload.options, 1)
            ],
            slot=slot_key,
            allow_manual_text=payload.allow_manual_text,
            manual_text_hint=payload.manual_text_hint or "如果这些建议都不合适，可以直接输入你自己的表述。",
        )

    def refine_prompt(
        self,
        template: TemplateSpec,
        prompt_spec: PromptSpec,
        prompt_text: str,
    ) -> str:
        try:
            payload = self._refine_chain.invoke(
                {
                    "mode_key": template.mode_key,
                    "confirmed_facts": prompt_spec.facts_snapshot,
                    "prompt_text": prompt_text,
                }
            )
        except Exception:  # noqa: BLE001
            payload = None
        if payload is None or not payload.refined_prompt:
            return prompt_text
        return payload.refined_prompt

    def repair_prompt(
        self,
        template: TemplateSpec,
        prompt_spec: PromptSpec,
        prompt_text: str,
        issues: list[ValidationIssue],
    ) -> str:
        try:
            payload = self._repair_chain.invoke(
                {
                    "mode_key": template.mode_key,
                    "confirmed_facts": prompt_spec.facts_snapshot,
                    "prompt_text": prompt_text,
                    "issues": [issue.model_dump(mode="json") for issue in issues],
                }
            )
        except Exception:  # noqa: BLE001
            payload = None
        if payload is None:
            return prompt_text
        return payload.repaired_prompt or payload.refined_prompt or prompt_text

    def propose_document_revision(
        self,
        template: TemplateSpec,
        document: SharedPromptDocument,
        section_key: str,
        instruction: str,
    ) -> ChoicePrompt | None:
        section = next((item for item in document.sections if item.key == section_key), None)
        if section is None:
            return None
        try:
            payload = self._doc_revision_chain.invoke(
                {
                    "mode_key": template.mode_key,
                    "section_key": section_key,
                    "section_text": section.content,
                    "instruction": instruction,
                    "confirmed_facts": {item.key: item.content for item in document.sections},
                }
            )
        except Exception:  # noqa: BLE001
            payload = None
        if payload is None or not payload.options:
            return None
        return ChoicePrompt(
            kind="doc_revision",
            title=payload.title,
            question=payload.question,
            options=[
                ChoiceOption(
                    key=str(idx),
                    label=option.label,
                    value=option.value,
                    rationale=option.rationale,
                )
                for idx, option in enumerate(payload.options, 1)
            ],
            section_key=section_key,
            allow_manual_text=payload.allow_manual_text,
            manual_text_hint=payload.manual_text_hint or "也可以直接输入你想要的改写。",
        )

    def _fallback_slot_choice_payload(
        self,
        template: TemplateSpec,
        state: SessionState,
        slot_key: str,
        slot_label: str,
        slot_question: str,
        slot_description: str,
        recent_user_text: str,
    ) -> SlotChoicePayload | None:
        try:
            raw_text = self._slot_choice_text_chain.invoke(
                {
                    "mode_key": template.mode_key,
                    "slot_key": slot_key,
                    "slot_label": slot_label,
                    "slot_question": slot_question,
                    "slot_description": slot_description,
                    "recent_user_message": recent_user_text,
                    "confirmed_facts": state.confirmed_slots,
                }
            )
        except Exception:  # noqa: BLE001
            self._debug("slot-choice fallback generation failed", exc_info=True)
            return None

        payload = parse_slot_choice_payload(raw_text, strict_json_only=False, default_slot=slot_key)
        if payload is None:
            self._debug(f"slot-choice fallback raw response rejected: {raw_text}")
        return payload

    def _debug(self, message: str, exc_info: bool = False) -> None:
        if not self.debug:
            return
        print(f"[hpa debug] {message}", file=sys.stderr)
        if exc_info:
            traceback.print_exc(file=sys.stderr)
