from __future__ import annotations

def apply_user_message_to_slots(state, user_text: str) -> dict:
    raise RuntimeError(
        "Rule-based extractor has been removed. "
        "Use the LLM-driven ClarificationService / SlotFillingService pipeline instead."
    )
