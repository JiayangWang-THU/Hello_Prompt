from __future__ import annotations

from pathlib import Path

from hpa.domain import SlotDefinition, TemplateCatalog, TemplateSpec

from .config_loader import load_structured_file

_LEGACY_KEY_ALIASES = {
    "env": "runtime_env",
    "os": "runtime_env",
    "output": "output_format",
    "format": "output_format",
    "tests": "acceptance_tests",
    "repo": "repo_context",
    "context": "repo_context",
    "features": "new_features",
    "compat": "compatibility",
    "system": "base_system",
}


class TemplateRepository:
    """Loads YAML/JSON template definitions into domain objects."""

    def __init__(self, path: str | Path = "configs/templates.yaml") -> None:
        self.path = Path(path)

    def load(self) -> TemplateCatalog:
        if not self.path.exists() and self.path.suffix.lower() in {".yaml", ".yml"}:
            fallback = self.path.with_suffix(".json")
            if fallback.exists():
                self.path = fallback
        if not self.path.exists():
            raise ValueError(f"无法加载模板配置：{self.path}")

        data = load_structured_file(self.path)
        if "slots" in data:
            return self._load_v2(data)
        return self._load_legacy(data)

    def _load_v2(self, data: dict) -> TemplateCatalog:
        slots_raw = data.get("slots")
        modes_raw = data.get("modes")
        if not isinstance(slots_raw, dict) or not isinstance(modes_raw, list):
            raise ValueError("templates 配置缺少 slots 或 modes")

        slots: dict[str, SlotDefinition] = {}
        aliases = dict(_LEGACY_KEY_ALIASES)
        for key, payload in slots_raw.items():
            if not isinstance(payload, dict):
                raise ValueError(f"slots[{key}] 必须是对象")
            slot = SlotDefinition(key=str(key), **payload)
            slots[slot.key] = slot
            aliases[slot.key] = slot.key
            for alias in slot.aliases:
                aliases[str(alias).strip().lower()] = slot.key

        templates: dict[str, TemplateSpec] = {}
        for payload in modes_raw:
            if not isinstance(payload, dict):
                raise ValueError("modes 中每一项必须是对象")
            template = TemplateSpec(
                category=str(payload.get("category", "")).strip().upper(),
                subtype=str(payload.get("subtype", "")).strip().upper(),
                label=str(payload.get("label", "")).strip(),
                description=str(payload.get("description", "")).strip(),
                required_slots=[str(item) for item in payload.get("required_slots", [])],
                slot_order=[str(item) for item in payload.get("slot_order", payload.get("required_slots", []))],
                deliverable_defaults=[str(item) for item in payload.get("deliverable_defaults", [])],
                acceptance_defaults=[str(item) for item in payload.get("acceptance_defaults", [])],
                output_format_default=str(
                    payload.get("output_format_default", "Markdown with clear headings and lists")
                ),
            )
            templates[template.mode_key] = template

        slot_priority = [str(item) for item in data.get("slot_priority", list(slots.keys()))]
        return TemplateCatalog(
            slots=slots,
            templates=templates,
            slot_priority=slot_priority,
            key_aliases=aliases,
        )

    def _load_legacy(self, data: dict) -> TemplateCatalog:
        modes_raw = data.get("modes")
        required_slots = data.get("required_slots")
        questions = data.get("questions", {})
        slot_priority = data.get("slot_priority", [])
        if not isinstance(modes_raw, list) or not isinstance(required_slots, dict):
            raise ValueError("legacy templates 配置缺少 modes 或 required_slots")

        known_sections = {
            "goal": "goal",
            "base_system": "context",
            "repo_context": "context",
            "new_features": "inputs",
            "language": "constraints",
            "runtime_env": "constraints",
            "scope": "constraints",
            "interfaces": "constraints",
            "compatibility": "constraints",
            "deliverable": "deliverables",
            "review_focus": "acceptance",
            "acceptance_tests": "acceptance",
            "output_format": "output",
        }
        known_labels = {
            "goal": "Goal",
            "base_system": "Base system constraints",
            "repo_context": "Repository context",
            "new_features": "Requested changes",
            "language": "Language / stack",
            "runtime_env": "Runtime environment",
            "scope": "Scope",
            "interfaces": "Interfaces",
            "compatibility": "Compatibility",
            "deliverable": "Requested deliverables",
            "review_focus": "Review focus",
            "acceptance_tests": "Acceptance tests",
            "output_format": "Output format",
        }

        all_slots = {slot for slots in required_slots.values() for slot in slots} | set(questions.keys())
        slots = {
            slot: SlotDefinition(
                key=slot,
                label=known_labels.get(slot, slot.replace("_", " ").title()),
                question=str(questions.get(slot, f"请补充：{slot}")),
                section=known_sections.get(slot, "constraints"),
                aliases=[alias for alias, target in _LEGACY_KEY_ALIASES.items() if target == slot],
            )
            for slot in all_slots
        }

        templates: dict[str, TemplateSpec] = {}
        for payload in modes_raw:
            category = str(payload.get("category", "")).strip().upper()
            subtype = str(payload.get("subtype", "")).strip().upper()
            key = f"{category}/{subtype}"
            templates[key] = TemplateSpec(
                category=category,
                subtype=subtype,
                label=str(payload.get("label", "")).strip(),
                required_slots=[str(item) for item in required_slots.get(key, [])],
                slot_order=[str(item) for item in slot_priority or required_slots.get(key, [])],
                deliverable_defaults=_default_deliverables(key),
                acceptance_defaults=_default_acceptance(key),
                output_format_default="Markdown with clear headings and lists",
            )

        aliases = dict(_LEGACY_KEY_ALIASES)
        for key in slots:
            aliases[key] = key
        return TemplateCatalog(
            slots=slots,
            templates=templates,
            slot_priority=[str(item) for item in slot_priority],
            key_aliases=aliases,
        )


def _default_deliverables(mode_key: str) -> list[str]:
    if mode_key == "CODE/REVIEW":
        return [
            "Prioritized findings with severity and evidence",
            "Actionable recommendations or refactor plan",
        ]
    if mode_key == "CODE/EXTEND":
        return [
            "Change plan and integration notes",
            "Key code snippets or patch guidance",
            "Test updates for new behavior",
        ]
    return [
        "Architecture / implementation plan",
        "Key code snippets and file layout",
        "Test plan aligned to acceptance criteria",
    ]


def _default_acceptance(mode_key: str) -> list[str]:
    if mode_key == "CODE/REVIEW":
        return ["Review checklist must be explicit and aligned to the goal"]
    return ["Include a concrete test checklist for the implemented changes"]
