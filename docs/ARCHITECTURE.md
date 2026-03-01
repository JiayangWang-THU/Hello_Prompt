# Architecture

## Product Boundary

Hello Prompt Agent is a CLI-first prompt clarification system.

- It is not a heavy autonomous coding agent.
- It is not a tool-calling platform by default.
- It grows a final prompt from user intent through structured clarification.

## Layers

### Domain

Pure business objects in `src/hpa/domain`:

- `TemplateSpec`
- `SlotDefinition`
- `PromptSpec`
- `SessionState`
- `ClarificationQuestion`
- `Suggestion`
- `ValidationIssue`
- `ComposerResult`

### Application

Workflow orchestration in `src/hpa/application`:

- `ClarificationService`
- `ModeResolverService`
- `SlotFillingService`
- `QuestionPlanningService`
- `PromptCompositionService`
- `ValidationService`
- `RepairService`
- `SessionService`

### Infrastructure

Adapters in `src/hpa/infrastructure`:

- YAML / JSON template loading
- LLM config loading
- session exporter
- LangChain-based LLM enhancer
- disabled capability provider

### Interfaces

CLI entrypoints in `src/hpa/interfaces`:

- `cli_agent.py`
- `cli_chat.py`

## Runtime Flow

1. Seed: user supplies an intent seed
2. Trunk: system confirms core facts
3. Branches: system asks mostly choice-based questions and records suggestions separately
4. Leaves: prompt draft is composed and optionally refined
5. Pruning: validator checks structure and repair may run if needed

## Fact Layer vs Suggestion Layer

- Confirmed user facts live in `SessionState.confirmed_slots`
- LLM suggestions live in `SessionState.suggestions`
- LLM extraction can only add facts supported by the current user message
- Suggested questions and optional improvements never overwrite confirmed facts
