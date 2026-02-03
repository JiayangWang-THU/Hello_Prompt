# Architecture

## Core Loop
1) Mode Selection (manual)
2) Slot filling (extractor)
3) Missing-slot detection (checklist + priority)
4) Ask-next-question
5) Compose final prompt

## Extensibility Points
- Router: manual -> rule-based -> LLM JSON router
- Extractor: last_asked_slot -> LLM slot extractor (multi-slot)
- Composer: single template -> per-mode template -> Jinja2 renderer
- Storage: save sessions / export prompt pack
