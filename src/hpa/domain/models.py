from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field


class SlotDefinition(BaseModel):
    """Defines one structured fact slot in the clarification workflow."""

    key: str
    label: str
    question: str
    section: Literal[
        "goal",
        "context",
        "inputs",
        "constraints",
        "deliverables",
        "acceptance",
        "output",
    ]
    aliases: list[str] = Field(default_factory=list)
    description: str = ""


class TemplateSpec(BaseModel):
    """A prompt template / mode that drives required facts and defaults."""

    category: str
    subtype: str
    label: str
    description: str = ""
    required_slots: list[str]
    slot_order: list[str] = Field(default_factory=list)
    deliverable_defaults: list[str] = Field(default_factory=list)
    acceptance_defaults: list[str] = Field(default_factory=list)
    output_format_default: str = "Markdown with clear headings and lists"

    @property
    def mode_key(self) -> str:
        return f"{self.category}/{self.subtype}"


class ChoiceOption(BaseModel):
    key: str
    label: str
    value: str
    rationale: str | None = None


class ChoicePrompt(BaseModel):
    kind: Literal["mode_select", "slot_select", "doc_revision"]
    title: str
    question: str
    options: list[ChoiceOption] = Field(default_factory=list)
    slot: str | None = None
    section_key: str | None = None
    allow_manual_text: bool = True
    manual_text_hint: str = ""
    source_user_text: str | None = None


class ClarificationQuestion(BaseModel):
    slot: str
    question: str
    source: Literal["llm", "system"] = "llm"


class Suggestion(BaseModel):
    kind: Literal["mode", "question", "repair", "capability", "note"] = "note"
    message: str
    source: Literal["rule", "llm", "system", "capability"] = "system"
    slot: str | None = None
    proposed_value: str | None = None
    rationale: str | None = None


class ValidationIssue(BaseModel):
    code: str
    severity: Literal["warning", "error"] = "error"
    message: str
    section: str | None = None
    slot: str | None = None


class PromptSpec(BaseModel):
    """Structured prompt representation built from confirmed facts."""

    mode_key: str
    role_lines: list[str] = Field(default_factory=list)
    goal: str = ""
    context_items: list[str] = Field(default_factory=list)
    input_items: list[str] = Field(default_factory=list)
    constraint_items: list[str] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    output_format: str = "Markdown with clear headings and lists"
    assumptions: list[str] = Field(default_factory=list)
    missing_info: list[str] = Field(default_factory=list)
    suggestion_items: list[str] = Field(default_factory=list)
    facts_snapshot: dict[str, str] = Field(default_factory=dict)


class PromptDocumentSection(BaseModel):
    key: str
    title: str
    content: str


class SharedPromptDocument(BaseModel):
    mode_key: str
    sections: list[PromptDocumentSection] = Field(default_factory=list)
    version: int = 1


class ComposerResult(BaseModel):
    prompt_spec: PromptSpec
    prompt_text: str
    document: SharedPromptDocument | None = None
    issues: list[ValidationIssue] = Field(default_factory=list)
    repaired: bool = False


@dataclass
class TurnRecord:
    role: Literal["user", "assistant"]
    content: str


@dataclass
class SessionState:
    """Mutable session state for the CLI workflow."""

    category: str | None = None
    subtype: str | None = None
    confirmed_slots: dict[str, str] = field(default_factory=dict)
    suggestions: list[Suggestion] = field(default_factory=list)
    pending_questions: list[ClarificationQuestion] = field(default_factory=list)
    pending_choice: ChoicePrompt | None = None
    history: list[TurnRecord] = field(default_factory=list)
    turn: int = 0
    last_asked_slot: str | None = None
    latest_result: ComposerResult | None = None
    latest_validation_issues: list[ValidationIssue] = field(default_factory=list)
    draft_text: str | None = None
    latest_document: SharedPromptDocument | None = None
    seed_intent: str | None = None

    @property
    def slots(self) -> dict[str, str]:
        return self.confirmed_slots

    def mode_key(self) -> str | None:
        if not self.category or not self.subtype:
            return None
        return f"{self.category}/{self.subtype}"
