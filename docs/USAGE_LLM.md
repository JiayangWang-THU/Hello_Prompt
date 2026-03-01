# LLM Usage

## Config Priority

Configuration order (high -> low):

1. CLI flags
2. Environment variables
3. `configs/llm.yaml`
4. Built-in defaults

Environment variables:

- `HPA_LLM_BASE_URL`
- `HPA_LLM_API_KEY`
- `HPA_LLM_MODEL`
- `HPA_LLM_TIMEOUT_SEC`
- `HPA_LLM_TEMPERATURE`
- `HPA_LLM_MAX_TOKENS`

## LangChain Notes

The agent pipeline is built on:

- `ChatPromptTemplate`
- composable `Runnable` chains
- structured JSON parsing with Pydantic schemas

`hpa agent` 现在默认依赖 LangChain LLM 节点；`hpa chat` 仍可在缺少 `langchain-openai` 时回退到 legacy OpenAI-compatible HTTP client。
