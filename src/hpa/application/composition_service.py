from __future__ import annotations

from hpa.domain import (
    ComposerResult,
    PromptDocumentSection,
    PromptSpec,
    SessionState,
    SharedPromptDocument,
    TemplateCatalog,
    TemplateSpec,
)

from .contracts import CapabilityProvider, LLMEnhancer


_SECTION_TITLES = {
    "goal": "Goal",
    "context": "Context / Inputs",
    "inputs": "Inputs / Requested Changes",
    "constraints": "Constraints",
    "deliverables": "Deliverables",
    "acceptance": "Acceptance Criteria",
    "output": "Output Format",
}


class PromptCompositionService:
    def __init__(
        self,
        catalog: TemplateCatalog,
        llm: LLMEnhancer | None = None,
        capability_provider: CapabilityProvider | None = None,
        enable_refinement: bool = False,
    ) -> None:
        self.catalog = catalog
        self.llm = llm
        self.capability_provider = capability_provider
        self.enable_refinement = enable_refinement

    def build_prompt_spec(self, state: SessionState, template: TemplateSpec) -> PromptSpec:
        role_lines = [
            "You are a senior software engineer helping turn a converged user demand into an executable prompt.",
            f"Mode: {template.mode_key}",
            "Preserve confirmed facts. Treat hypotheses and suggestions as optional unless the user confirms them.",
        ]
        grouped: dict[str, list[str]] = {
            "context": [],
            "inputs": [],
            "constraints": [],
            "deliverables": [],
            "acceptance": [],
        }

        ordered_slots: list[str] = []
        seen: set[str] = set()
        for slot in template.slot_order or template.required_slots:
            if slot not in seen:
                ordered_slots.append(slot)
                seen.add(slot)
        for slot in self.catalog.slot_priority:
            if slot in state.confirmed_slots and slot not in seen:
                ordered_slots.append(slot)
                seen.add(slot)
        for slot in state.confirmed_slots:
            if slot not in seen:
                ordered_slots.append(slot)
                seen.add(slot)

        for slot in ordered_slots:
            value = state.confirmed_slots.get(slot, "").strip()
            if not value:
                continue
            slot_def = self.catalog.slots.get(slot)
            if slot_def is None:
                grouped["constraints"].append(f"{slot}: {value}")
                continue
            if slot_def.section == "goal":
                continue
            if slot_def.section == "output":
                continue
            grouped[slot_def.section].append(f"{slot_def.label}: {value}")

        deliverables = grouped["deliverables"] or list(template.deliverable_defaults)
        acceptance = grouped["acceptance"] or list(template.acceptance_defaults)
        output_format = (
            state.confirmed_slots.get("output_format", "").strip()
            or template.output_format_default
        )
        missing = [self.catalog.slots.get(slot, None) for slot in template.required_slots]
        missing_info = [
            spec.label if spec is not None else slot
            for slot, spec in zip(template.required_slots, missing)
            if not state.confirmed_slots.get(slot, "").strip()
        ]

        assumptions = [
            f"Not specified: {slot_def.label} (use reasonable defaults)"
            for key, slot_def in self.catalog.slots.items()
            if key not in template.required_slots and not state.confirmed_slots.get(key, "").strip()
        ]

        suggestion_items = [suggestion.message for suggestion in state.suggestions]
        prompt_spec = PromptSpec(
            mode_key=template.mode_key,
            role_lines=role_lines,
            goal=state.confirmed_slots.get("goal", "").strip(),
            context_items=grouped["context"],
            input_items=grouped["inputs"],
            constraint_items=grouped["constraints"],
            deliverables=deliverables,
            acceptance_criteria=acceptance,
            output_format=output_format,
            assumptions=assumptions if not missing_info else [],
            missing_info=missing_info,
            suggestion_items=suggestion_items,
            facts_snapshot=dict(state.confirmed_slots),
        )
        return prompt_spec

    def render_prompt(self, prompt_spec: PromptSpec) -> str:
        return self.render_document(self.build_document(prompt_spec))

    def build_document(self, prompt_spec: PromptSpec) -> SharedPromptDocument:
        sections: list[PromptDocumentSection] = [
            PromptDocumentSection(
                key="role",
                title="Role",
                content="\n".join(f"- {line}" for line in prompt_spec.role_lines) or "- (none)",
            ),
            PromptDocumentSection(
                key="goal",
                title="Goal",
                content=f"- {prompt_spec.goal or '(missing)'}",
            ),
            PromptDocumentSection(
                key="context",
                title="Context / Inputs",
                content=self._render_items(prompt_spec.context_items),
            ),
            PromptDocumentSection(
                key="inputs",
                title="Inputs / Requested Changes",
                content=self._render_items(prompt_spec.input_items),
            ),
            PromptDocumentSection(
                key="constraints",
                title="Constraints",
                content=self._render_items(prompt_spec.constraint_items),
            ),
            PromptDocumentSection(
                key="deliverables",
                title="Deliverables",
                content=self._render_items(prompt_spec.deliverables),
            ),
            PromptDocumentSection(
                key="acceptance",
                title="Acceptance Criteria",
                content=self._render_items(prompt_spec.acceptance_criteria),
            ),
            PromptDocumentSection(
                key="output",
                title="Output Format",
                content=self._render_items([prompt_spec.output_format]),
            ),
        ]
        if prompt_spec.assumptions:
            sections.append(
                PromptDocumentSection(
                    key="assumptions",
                    title="Assumptions",
                    content=self._render_items(prompt_spec.assumptions),
                )
            )
        if prompt_spec.suggestion_items:
            sections.append(
                PromptDocumentSection(
                    key="suggestions",
                    title="Suggestion Layer",
                    content=self._render_items(prompt_spec.suggestion_items),
                )
            )
        if prompt_spec.missing_info:
            sections.append(
                PromptDocumentSection(
                    key="missing",
                    title="Missing Info",
                    content=self._render_items(prompt_spec.missing_info),
                )
            )
        return SharedPromptDocument(mode_key=prompt_spec.mode_key, sections=sections)

    def render_document(self, document: SharedPromptDocument) -> str:
        lines: list[str] = []
        for section in document.sections:
            lines.append(f"## {section.title}")
            lines.append(section.content or "- (none)")
            lines.append("")

        return "\n".join(lines).rstrip()

    def apply_document_section(
        self,
        document: SharedPromptDocument,
        section_key: str,
        new_content: str,
    ) -> SharedPromptDocument:
        updated_sections: list[PromptDocumentSection] = []
        changed = False
        for section in document.sections:
            if section.key == section_key:
                updated_sections.append(
                    PromptDocumentSection(
                        key=section.key,
                        title=section.title,
                        content=new_content.strip(),
                    )
                )
                changed = True
            else:
                updated_sections.append(section)
        if not changed:
            raise ValueError(f"未找到 section：{section_key}")
        return SharedPromptDocument(
            mode_key=document.mode_key,
            sections=updated_sections,
            version=document.version + 1,
        )

    def _render_items(self, items: list[str]) -> str:
        if not items:
            return "- (none)"
        return "\n".join(f"- {item}" for item in items)

    def compose(self, state: SessionState, template: TemplateSpec) -> ComposerResult:
        prompt_spec = self.build_prompt_spec(state, template)
        document = self.build_document(prompt_spec)
        prompt_text = self.render_document(document)

        if self.capability_provider is not None:
            capability_suggestions = self.capability_provider.suggest("compose", template, state, prompt_spec)
            if capability_suggestions:
                state.suggestions.extend(capability_suggestions)
                prompt_spec.suggestion_items = [suggestion.message for suggestion in state.suggestions]
                document = self.build_document(prompt_spec)
                prompt_text = self.render_document(document)

        if self.enable_refinement and self.llm is not None and not prompt_spec.missing_info:
            prompt_text = self.llm.refine_prompt(template, prompt_spec, prompt_text)
            document = self.build_document(prompt_spec)

        return ComposerResult(prompt_spec=prompt_spec, prompt_text=prompt_text, document=document)
