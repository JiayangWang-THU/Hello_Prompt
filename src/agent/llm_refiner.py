from __future__ import annotations

from .json_utils import extract_first_json_object, safe_parse_json_object

ALLOWED_HEADINGS = {
    "Role",
    "Context / Inputs",
    "Goal",
    "Constraints",
    "Deliverables",
    "Acceptance Criteria",
    "Output Format",
    "Assumptions",
    "Missing Info",
}

SYSTEM_PROMPT = (
    "You refine the language of a structured prompt.\n"
    "Return ONLY one JSON object. No markdown, no explanation.\n"
    "Schema: {\"refined\": \"<text>\"}.\n"
    "Do NOT add or remove any section headings."
)


def _extract_headings(text: str) -> set[str]:
    headings = set()
    for line in text.splitlines():
        if line.startswith("## "):
            headings.add(line[3:].strip())
    return headings


def refine_prompt(client, base_prompt: str, strict_json_only: bool = True) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": base_prompt},
    ]

    try:
        response = client.chat(messages)
    except Exception:  # noqa: BLE001
        return base_prompt

    raw_json = response.strip() if strict_json_only else extract_first_json_object(response)
    if not raw_json:
        return base_prompt

    parsed = safe_parse_json_object(raw_json)
    if not parsed:
        return base_prompt

    refined = parsed.get("refined")
    if not isinstance(refined, str) or not refined.strip():
        return base_prompt

    base_headings = _extract_headings(base_prompt)
    refined_headings = _extract_headings(refined)
    if refined_headings != base_headings:
        return base_prompt
    if not refined_headings.issubset(ALLOWED_HEADINGS):
        return base_prompt

    return refined
