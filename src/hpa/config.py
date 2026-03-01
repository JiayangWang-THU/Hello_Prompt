from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hpa.domain import TemplateCatalog
from hpa.infrastructure import TemplateRepository


@dataclass(frozen=True)
class TemplatesConfig:
    catalog: TemplateCatalog

    @staticmethod
    def load(path: str | Path = "configs/templates.yaml") -> "TemplatesConfig":
        return TemplatesConfig(catalog=TemplateRepository(path).load())

    @property
    def modes(self):
        return [
            {
                "category": template.category,
                "subtype": template.subtype,
                "label": template.label,
            }
            for template in self.catalog.templates.values()
        ]

    @property
    def required_slots(self):
        return {
            template.mode_key: list(template.required_slots)
            for template in self.catalog.templates.values()
        }

    @property
    def slot_priority(self):
        return list(self.catalog.slot_priority)

    @property
    def questions(self):
        return {key: slot.question for key, slot in self.catalog.slots.items()}

    def normalize_key(self, key: str) -> str:
        return self.catalog.normalize_key(key)

    def allowed_modes(self) -> set[tuple[str, str]]:
        return self.catalog.allowed_modes()

    def mode_menu_text(self) -> str:
        return self.catalog.mode_menu_text()


def normalize_key_name(key: str) -> str:
    return TemplateRepository("configs/templates.yaml").load().normalize_key(key)
