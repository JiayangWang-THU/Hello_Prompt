# Architecture

## Core Loop
1) Mode Selection (manual)
2) Slot filling (extractor)
3) Missing-slot detection (checklist + priority)
4) Ask-next-question
5) Compose final prompt

## Recent Enhancements
- Extractor: JSON + multi-line key/value + alias normalization
- Engine: /show, /clear, /export commands
- CLI: /paste multi-line input support
- Composer: per-mode prompt sections with defensive missing-info handling

## Extensibility Points
- Router: manual -> rule-based -> LLM JSON router
- Extractor: last_asked_slot -> LLM slot extractor (multi-slot)
- Composer: single template -> per-mode template -> Jinja2 renderer
- Storage: save sessions / export prompt pack
