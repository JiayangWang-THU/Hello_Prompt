from __future__ import annotations

from .config import TemplatesConfig
from .state import AgentState

_ALL_SLOTS = [
    "goal",
    "base_system",
    "repo_context",
    "new_features",
    "compatibility",
    "language",
    "runtime_env",
    "scope",
    "interfaces",
    "deliverable",
    "review_focus",
    "acceptance_tests",
    "output_format",
]

_LABELS = {
    "goal": "Goal",
    "base_system": "Base system constraints",
    "repo_context": "Repository context",
    "new_features": "New features",
    "compatibility": "Compatibility",
    "language": "Language/stack",
    "runtime_env": "Runtime environment",
    "scope": "Scope",
    "interfaces": "Interfaces",
    "deliverable": "Requested deliverables",
    "review_focus": "Review focus",
    "acceptance_tests": "Acceptance tests",
    "output_format": "Output format",
}


def _slot_value(state: AgentState, key: str) -> str:
    return state.slots.get(key, "").strip()


def _add_section(lines: list[str], title: str, items: list[str]) -> None:
    lines.append(f"## {title}")
    if items:
        lines.extend(items)
    else:
        lines.append("- (none)")
    lines.append("")


def _missing_required(state: AgentState, cfg: TemplatesConfig) -> list[str]:
    mode_key = state.mode_key() or ""
    required = cfg.required_slots.get(mode_key, [])
    return [s for s in required if not _slot_value(state, s)]


def _assumptions(state: AgentState, cfg: TemplatesConfig) -> list[str]:
    mode_key = state.mode_key() or ""
    required = set(cfg.required_slots.get(mode_key, []))
    optional = [s for s in _ALL_SLOTS if s not in required]
    missing_optional = [s for s in optional if not _slot_value(state, s)]
    return [f"- Not specified: {_LABELS.get(s, s)} (assume reasonable defaults)" for s in missing_optional]


def _default_deliverables(mode_key: str) -> list[str]:
    if mode_key == "CODE/REVIEW":
        return [
            "- Prioritized findings with severity and evidence",
            "- Actionable recommendations or refactor plan",
        ]
    if mode_key == "CODE/EXTEND":
        return [
            "- Change plan and integration notes",
            "- Key code snippets or patch guidance",
            "- Test updates for new behavior",
        ]
    return [
        "- Architecture/implementation plan",
        "- Key code snippets and file layout",
        "- Test plan aligned to acceptance criteria",
    ]


def compose_prompt(state: AgentState, cfg: TemplatesConfig) -> str:
    """Per-mode prompt composer for CODE/* templates."""
    mode_key = state.mode_key() or "UNKNOWN"
    s = state.slots
    lines: list[str] = []

    _add_section(lines, "Role", [
        "- You are a senior software engineer and prompt engineer.",
        f"- Mode: {mode_key}",
    ])

    context_items: list[str] = []
    for key in ["base_system", "repo_context", "new_features"]:
        if _slot_value(state, key):
            context_items.append(f"- {_LABELS[key]}: {s[key].strip()}")
    _add_section(lines, "Context / Inputs", context_items)

    _add_section(lines, "Goal", [f"- {_slot_value(state, 'goal') or '(missing)'}"])

    constraint_items: list[str] = []
    for key in ["runtime_env", "language", "compatibility", "scope", "interfaces"]:
        if _slot_value(state, key):
            constraint_items.append(f"- {_LABELS[key]}: {s[key].strip()}")
    _add_section(lines, "Constraints", constraint_items)

    deliverable_items: list[str] = []
    if _slot_value(state, "deliverable"):
        deliverable_items.append(f"- {_slot_value(state, 'deliverable')}")
    else:
        deliverable_items.extend(_default_deliverables(mode_key))
    _add_section(lines, "Deliverables", deliverable_items)

    acceptance_items: list[str] = []
    if mode_key == "CODE/REVIEW":
        if _slot_value(state, "review_focus"):
            acceptance_items.append(f"- Review checklist focuses on: {_slot_value(state, 'review_focus')}")
        else:
            acceptance_items.append("- Review checklist must be explicit and aligned to the goals")
    else:
        if _slot_value(state, "acceptance_tests"):
            acceptance_items.append(f"- Acceptance tests: {_slot_value(state, 'acceptance_tests')}")
        else:
            acceptance_items.append("- Include a concrete test checklist for the implemented changes")
    _add_section(lines, "Acceptance Criteria", acceptance_items)

    output_value = _slot_value(state, "output_format") or "Markdown with clear headings and lists"
    _add_section(lines, "Output Format", [f"- {output_value}"])

    missing_required = _missing_required(state, cfg)
    if not missing_required:
        assumptions = _assumptions(state, cfg)
        if assumptions:
            _add_section(lines, "Assumptions", assumptions)

    if missing_required:
        _add_section(lines, "Missing Info", [f\"- {_LABELS.get(s, s)}\" for s in missing_required])

    return "\n".join(lines).rstrip()
