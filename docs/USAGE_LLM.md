# LLM Usage

## Config Priority

优先级从高到低：

1. CLI 参数
2. 环境变量
3. `configs/llm.yaml`
4. 默认值

支持的环境变量：

- `HPA_LLM_BASE_URL`
- `HPA_LLM_API_KEY`
- `HPA_LLM_MODEL`
- `HPA_LLM_TIMEOUT_SEC`
- `HPA_LLM_TEMPERATURE`
- `HPA_LLM_MAX_TOKENS`

## Model Access

项目默认按 OpenAI-compatible 接口访问模型。  
`build_langchain_chat_model()` 会对 base URL 做 `/v1` 归一化，并在本地地址下关闭代理继承。

默认配置见 `configs/llm.yaml`：

- `base_url`: `http://127.0.0.1:8080`
- `model`: `Qwen3-4B-Q4_K_M.gguf`

## Where LLM Is Used

LLM 参与这些环节：

- mode 推荐
- slot 提取
- 收敛焦点的 top-k 假设生成
- prompt refinement
- repair
- 文档 section revise

## Runtime Behavior

- `hpa agent` 依赖 LangChain 风格的 chat model 接入
- `hpa web` 复用同一套 agent service，因此也依赖同样的 LLM 配置
- `hpa chat` 在 LangChain 不可用时，可以回退到 legacy OpenAI-compatible HTTP client
- agent 主路径不是让模型一次性输出最终 prompt，而是让模型多轮猜测并逐步收敛需求

## Notes

- 如果本地没有安装 `langchain-openai`，`hpa agent` 和 `hpa web` 无法启动
- 测试使用 fake LLM，不依赖真实联网模型
