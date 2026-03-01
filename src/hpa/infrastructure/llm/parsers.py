from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel, Field, ValidationError

from hpa.utils.json_utils import extract_first_json_object

ModelT = TypeVar("ModelT", bound=BaseModel)


class SlotExtractionPayload(BaseModel):
    updates: dict[str, str] = Field(default_factory=dict)


class ChoiceOptionPayload(BaseModel):
    label: str
    value: str
    rationale: str | None = None


class ModeRoutingPayload(BaseModel):
    title: str = "请选择一个 mode"
    question: str = "输入数字选择最接近的任务类型。"
    recommended_mode: str | None = None
    reason: str | None = None
    allow_manual_text: bool = True


class SlotChoicePayload(BaseModel):
    slot: str | None = None
    title: str = ""
    question: str = ""
    options: list[ChoiceOptionPayload] = Field(default_factory=list)
    allow_manual_text: bool = True
    manual_text_hint: str = ""
    suggestions: list[str] = Field(default_factory=list)


class PromptTextPayload(BaseModel):
    refined_prompt: str | None = None
    repaired_prompt: str | None = None


class DocRevisionPayload(BaseModel):
    section_key: str
    title: str
    question: str
    options: list[ChoiceOptionPayload] = Field(default_factory=list)
    allow_manual_text: bool = True
    manual_text_hint: str = ""


def parse_pydantic_json(model_cls: type[ModelT], text: str, strict_json_only: bool) -> ModelT | None:
    raw_text = text.strip()
    candidate = raw_text if strict_json_only else (extract_first_json_object(raw_text) or "")
    if not candidate:
        return None
    try:
        return model_cls.model_validate_json(candidate)
    except ValidationError:
        return None


def parse_slot_choice_payload(text: str, strict_json_only: bool, default_slot: str) -> SlotChoicePayload | None:
    payload = parse_pydantic_json(SlotChoicePayload, text, strict_json_only)
    if payload is not None and payload.options:
        if not payload.slot:
            payload.slot = default_slot
        return payload

    raw_text = text.strip()
    candidate = raw_text if strict_json_only else (extract_first_json_object(raw_text) or "")
    if candidate:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            coerced = _coerce_slot_choice_dict(data, default_slot)
            if coerced is not None:
                return coerced

    return _parse_slot_choice_from_lines(raw_text, default_slot)


def _coerce_slot_choice_dict(data: dict[str, object], default_slot: str) -> SlotChoicePayload | None:
    raw_options = data.get("options", [])
    options: list[ChoiceOptionPayload] = []
    if isinstance(raw_options, list):
        for item in raw_options:
            if isinstance(item, str):
                label = item.strip()
                if label:
                    options.append(ChoiceOptionPayload(label=label, value=label))
                continue
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or item.get("value") or "").strip()
            value = str(item.get("value") or label).strip()
            rationale = item.get("rationale")
            if label and value:
                options.append(
                    ChoiceOptionPayload(
                        label=label,
                        value=value,
                        rationale=str(rationale).strip() if rationale is not None else None,
                    )
                )
    if not options:
        return None
    return SlotChoicePayload(
        slot=str(data.get("slot") or default_slot),
        title=str(data.get("title") or ""),
        question=str(data.get("question") or ""),
        options=options,
        allow_manual_text=bool(data.get("allow_manual_text", True)),
        manual_text_hint=str(data.get("manual_text_hint") or ""),
        suggestions=[str(item).strip() for item in data.get("suggestions", []) if str(item).strip()]
        if isinstance(data.get("suggestions"), list)
        else [],
    )


def _parse_slot_choice_from_lines(text: str, default_slot: str) -> SlotChoicePayload | None:
    bullet_pattern = re.compile(r"^\s*(?:[-*]|\d+[.)]|[A-Za-z][.)])\s*(.+?)\s*$")
    options: list[ChoiceOptionPayload] = []
    for line in text.splitlines():
        match = bullet_pattern.match(line)
        if not match:
            continue
        label = match.group(1).strip()
        if not label:
            continue
        options.append(ChoiceOptionPayload(label=label, value=label))
        if len(options) >= 4:
            break

    if not options:
        return None

    return SlotChoicePayload(
        slot=default_slot,
        title="",
        question="",
        options=options,
        allow_manual_text=True,
        manual_text_hint="如果这些建议都不合适，可以直接输入你自己的表述。",
    )
