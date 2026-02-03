# LLM Usage

## 配置优先级
配置合并顺序（高 -> 低）：
1. CLI 参数
2. 环境变量
3. YAML 配置文件（`configs/llm.yaml`）
4. 默认值

环境变量前缀：
- `HPA_LLM_BASE_URL`
- `HPA_LLM_API_KEY`
- `HPA_LLM_MODEL`
- `HPA_LLM_TIMEOUT_SEC`
- `HPA_LLM_TEMPERATURE`
- `HPA_LLM_MAX_TOKENS`

## /paste 使用
进入粘贴模式后，输入多行内容，以单独一行 `.` 结束，作为一条 user message 发送。

## 安全注意
- 不要在仓库中提交 `api_key`
- CLI 与日志中不会输出 key
