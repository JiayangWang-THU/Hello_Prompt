from __future__ import annotations

from hpa.application import (
    ClarificationService,
    ModeResolverService,
    PromptCompositionService,
    QuestionPlanningService,
    RepairService,
    SessionService,
    SlotFillingService,
    ValidationService,
)
from hpa.domain import ChoiceOption, ChoicePrompt, PromptSpec, SessionState, SharedPromptDocument, TemplateCatalog, TemplateSpec, ValidationIssue
from hpa.infrastructure import SessionExporter, TemplateRepository
from hpa.infrastructure.capability_provider import DisabledCapabilityProvider


class FakeLLMEnhancer:
    def __init__(
        self,
        *,
        mode_choice: ChoicePrompt | None = None,
        slot_updates: dict[str, str] | None = None,
        slot_choice: ChoicePrompt | None = None,
        refined_prompt: str | None = None,
        repaired_prompt: str | None = None,
        doc_revision: ChoicePrompt | None = None,
    ) -> None:
        self.mode_choice = mode_choice
        self.slot_updates = slot_updates or {}
        self.slot_choice = slot_choice
        self.refined_prompt = refined_prompt
        self.repaired_prompt = repaired_prompt
        self.doc_revision = doc_revision

    def propose_mode_choice(self, catalog: TemplateCatalog, user_text: str) -> ChoicePrompt | None:
        return self.mode_choice

    def extract_slots(
        self,
        catalog: TemplateCatalog,
        template: TemplateSpec,
        state: SessionState,
        user_text: str,
    ) -> dict[str, str]:
        return dict(self.slot_updates)

    def propose_slot_choice(
        self,
        catalog: TemplateCatalog,
        template: TemplateSpec,
        state: SessionState,
        slot: str,
        recent_user_text: str,
    ) -> ChoicePrompt | None:
        return self.slot_choice

    def refine_prompt(self, template: TemplateSpec, prompt_spec: PromptSpec, prompt_text: str) -> str:
        return self.refined_prompt or prompt_text

    def repair_prompt(
        self,
        template: TemplateSpec,
        prompt_spec: PromptSpec,
        prompt_text: str,
        issues: list[ValidationIssue],
    ) -> str:
        return self.repaired_prompt or prompt_text

    def propose_document_revision(
        self,
        template: TemplateSpec,
        document: SharedPromptDocument,
        section_key: str,
        instruction: str,
    ) -> ChoicePrompt | None:
        return self.doc_revision


def load_catalog() -> TemplateCatalog:
    return TemplateRepository("configs/templates.yaml").load()


def build_service(
    *,
    llm: FakeLLMEnhancer | None = None,
    enable_mode_router: bool = True,
    enable_refinement: bool = False,
    enable_repair: bool = False,
) -> ClarificationService:
    catalog = load_catalog()
    llm = llm or FakeLLMEnhancer()
    return ClarificationService(
        catalog=catalog,
        mode_service=ModeResolverService(catalog, llm=llm, enable_mode_router=enable_mode_router),
        slot_service=SlotFillingService(
            catalog,
            llm=llm,
        ),
        question_service=QuestionPlanningService(
            catalog,
            llm=llm,
        ),
        composition_service=PromptCompositionService(
            catalog,
            llm=llm,
            capability_provider=DisabledCapabilityProvider(),
            enable_refinement=enable_refinement,
        ),
        validation_service=ValidationService(catalog),
        repair_service=RepairService(llm=llm, enable_repair=enable_repair),
        session_service=SessionService(catalog, SessionExporter()),
        llm=llm,
    )


def make_mode_choice(recommended: str = "CODE/EXTEND") -> ChoicePrompt:
    modes = [
        ("CODE/EXTEND", "二次开发 / 加功能"),
        ("CODE/REVIEW", "审阅项目结构"),
        ("CODE/FROM_SCRATCH", "从零构建"),
    ]
    ordered = [item for item in modes if item[0] == recommended] + [item for item in modes if item[0] != recommended]
    return ChoicePrompt(
        kind="mode_select",
        title="请选择一个 mode",
        question="输入数字选择最接近的任务类型。",
        options=[
            ChoiceOption(key=str(idx), label=f"{mode} ({label})", value=mode, rationale=label)
            for idx, (mode, label) in enumerate(ordered, 1)
        ],
        allow_manual_text=True,
        manual_text_hint="继续补充一句任务描述也可以。",
        source_user_text="seed",
    )


def make_slot_choice(slot: str, *values: str) -> ChoicePrompt:
    return ChoicePrompt(
        kind="slot_select",
        title=f"请补全 {slot}",
        question=f"为 {slot} 选择一个更接近的候选答案。",
        options=[
            ChoiceOption(key=str(idx), label=value, value=value, rationale="LLM suggestion")
            for idx, value in enumerate(values, 1)
        ],
        slot=slot,
        allow_manual_text=True,
        manual_text_hint="如果这些都不合适，可以直接输入你的表述。",
    )
