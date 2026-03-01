from __future__ import annotations

from dataclasses import dataclass

from .models import SlotDefinition, TemplateSpec


@dataclass(frozen=True)
class TemplateCatalog:
    slots: dict[str, SlotDefinition]
    templates: dict[str, TemplateSpec]
    slot_priority: list[str]
    key_aliases: dict[str, str]

    def normalize_key(self, key: str) -> str:
        normalized = key.strip().lower()
        return self.key_aliases.get(normalized, normalized)

    def get_template(self, mode_key: str) -> TemplateSpec | None:
        return self.templates.get(mode_key)

    def allowed_modes(self) -> set[tuple[str, str]]:
        return {
            (template.category.upper(), template.subtype.upper())
            for template in self.templates.values()
        }

    def mode_menu_text(self) -> str:
        lines = ["请选择模式（Prompt Clarification Framework）："]
        for idx, template in enumerate(self.templates.values(), 1):
            label = template.label or template.description or ""
            lines.append(f"{idx}) /mode {template.category} {template.subtype}  （{label}）")
        lines.append("示例：/mode CODE EXTEND")
        return "\n".join(lines)

    def slot_question(self, slot: str) -> str:
        spec = self.slots.get(slot)
        if spec is None:
            return f"请补充：{slot}"
        return spec.question

