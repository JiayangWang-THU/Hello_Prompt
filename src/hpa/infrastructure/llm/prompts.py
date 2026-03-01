from __future__ import annotations

SLOT_EXTRACTION_SYSTEM = """You extract confirmed facts from a user's clarification message.
Return only JSON.
Schema:
{
  "updates": {"slot_key": "value"}
}
Rules:
- Only extract facts directly supported by the latest user message.
- Never invent missing facts.
- Never contradict already confirmed facts.
- Only use allowed_slots.
"""

MODE_ROUTING_SYSTEM = """You are helping a CLI user choose the right prompt mode.
Return only JSON.
Schema:
{
  "title": "...",
  "question": "...",
  "recommended_mode": "CATEGORY/SUBTYPE" or null,
  "reason": "...",
  "allow_manual_text": true
}
Rules:
- Recommend a mode if the task intent is reasonably clear.
- Keep the wording concise.
"""

SLOT_CHOICE_SYSTEM = """You are planning the next clarification question for a prompt-growth workflow.
Return only JSON.
Schema:
{
  "title": "...",
  "question": "...",
  "options": [
    {"label": "...", "value": "...", "rationale": "..."}
  ],
  "allow_manual_text": true,
  "manual_text_hint": "..."
}
Rules:
- The target slot is already chosen by the system. Do not change the slot.
- Prefer 2-4 short answer choices.
- Choices should be concise, plausible suggestions for the target slot, not fabricated facts.
- Use the recent_user_message and slot_description to stay close to what the user just said.
- The user may still type a custom answer.
"""

SLOT_CHOICE_TEXT_FALLBACK_SYSTEM = """You are helping a CLI user fill one specific prompt slot.
Output only 2-4 short candidate answers as plain text.
Rules:
- Do not write any introduction.
- One option per line.
- Each line must start with '- '.
- Stay close to the recent user message and confirmed facts.
- Do not invent detailed facts that the user never implied.
"""

REFINE_SYSTEM = """You refine a structured prompt draft.
Return only JSON.
Schema:
{"refined_prompt": "..."}
Rules:
- Preserve all confirmed facts.
- Preserve section headings.
- Do not remove constraints, deliverables, or acceptance criteria.
"""

REPAIR_SYSTEM = """You repair a structured prompt draft using validation issues.
Return only JSON.
Schema:
{"repaired_prompt": "..."}
Rules:
- Fix only the reported issues.
- Preserve confirmed facts exactly.
- Preserve section headings.
"""

DOC_REVISION_SYSTEM = """You help revise one section of a shared prompt document.
Return only JSON.
Schema:
{
  "section_key": "...",
  "title": "...",
  "question": "...",
  "options": [
    {"label": "...", "value": "...", "rationale": "..."}
  ],
  "allow_manual_text": true,
  "manual_text_hint": "..."
}
Rules:
- Preserve confirmed facts.
- Revise only the requested section.
- Offer 2-3 concise alternatives.
"""
