from __future__ import annotations

from pathlib import Path

import pytest

from hpa.composer import compose_prompt
from hpa.config import TemplatesConfig
from hpa.state import AgentState


def _cfg() -> TemplatesConfig:
    root = Path(__file__).resolve().parents[1]
    return TemplatesConfig.load(root / "configs" / "templates.yaml")


@pytest.mark.parametrize(
    "mode_key, slots, expected_phrase",
    [
        (
            "CODE/FROM_SCRATCH",
            {
                "goal": "build tool",
                "language": "Python",
                "runtime_env": "Ubuntu",
                "scope": "do A; not B",
                "interfaces": "CLI",
                "acceptance_tests": "test1; test2",
                "output_format": "Markdown",
            },
            "Acceptance tests",
        ),
        (
            "CODE/REVIEW",
            {
                "goal": "review project",
                "repo_context": "tree summary",
                "review_focus": "architecture",
                "deliverable": "issues list",
                "output_format": "Markdown",
            },
            "Review checklist",
        ),
        (
            "CODE/EXTEND",
            {
                "goal": "add feature",
                "base_system": "existing service",
                "new_features": "P0 x",
                "compatibility": "keep old API",
                "runtime_env": "Ubuntu",
                "output_format": "Markdown",
            },
            "test checklist",
        ),
    ],
)
def test_composer_sections(mode_key, slots, expected_phrase):
    cat, sub = mode_key.split("/")
    state = AgentState(category=cat, subtype=sub, slots=slots)
    prompt = compose_prompt(state, _cfg())
    for section in [
        "## Role",
        "## Context / Inputs",
        "## Goal",
        "## Constraints",
        "## Deliverables",
        "## Acceptance Criteria",
        "## Output Format",
    ]:
        assert section in prompt
    assert expected_phrase in prompt
