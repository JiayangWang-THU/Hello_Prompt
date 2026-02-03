from __future__ import annotations

from hpa.config import TemplatesConfig
from hpa.state import AgentState

from .json_utils import extract_first_json_object, safe_parse_json_object

SYSTEM_PROMPT = (
    "You generate clarification questions for missing slots in a CODE workflow.\n"
    "Return ONLY one JSON object. No markdown, no explanation.\n"
    "Schema: {\"ask\": [{\"slot\": \"<missing_slot>\", \"question\": \"...\"}, ...]}.\n"
    "You MUST only ask about missing_slots. Ask at most 2."
)


def _build_user_prompt(mode_key: str, missing_slots: list[str]) -> str:
    lines = [
        f"mode_key: {mode_key}",
        f"missing_slots: {missing_slots}",
    ]
    return "\n".join(lines)


def generate_questions(
    client,
    cfg: TemplatesConfig,
    state: AgentState,
    missing: list[str],
    strict_json_only: bool = True,
) -> list[dict[str, str]]:
    if not missing:
        return []
    mode_key = state.mode_key()
    if not mode_key:
        return []

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_prompt(mode_key, missing)},
    ]

    try:
        response = client.chat(messages)
    except Exception:  # noqa: BLE001
        return []

    raw_json = response.strip() if strict_json_only else extract_first_json_object(response)
    if not raw_json:
        return []
    parsed = safe_parse_json_object(raw_json)
    if not parsed:
        return []
    ask = parsed.get("ask")
    if not isinstance(ask, list):
        return []

    missing_set = {cfg.normalize_key(s) for s in missing}
    results: list[dict[str, str]] = []
    for item in ask[:2]:
        if not isinstance(item, dict):
            continue
        raw_slot = item.get("slot")
        question = item.get("question")
        if not isinstance(raw_slot, str) or not isinstance(question, str):
            continue
        slot = cfg.normalize_key(raw_slot)
        q = question.strip()
        if not q or len(q) > 200:
            continue
        if slot not in missing_set:
            continue
        results.append({"slot": slot, "question": q})

    return results
