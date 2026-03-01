# Hello Prompt Agent

Hello Prompt Agent 是一个 **CLI-first 的 Prompt Clarification Framework**。  
它不是通用 autonomous agent，也不默认替用户自主规划一切。它的核心目标是把模糊需求逐步澄清成结构化、高质量 prompt，供 Codex 或其他代码 LLM 使用。

## 当前定位

- 本地 Python 包 + CLI
- 模板 / slots 驱动的需求澄清器
- 以“事实层 + 建议层”分离为核心
- LLM 驱动交互，尽量通过选择题推进
- 支持最小可用的 validation + repair 闭环

## 主要命令

### `hpa agent`

进入 LLM 驱动、选择题优先的 prompt clarification 工作流。

```bash
hpa agent
```

支持命令：

- `/templates`
- `/mode <CATEGORY> <SUBTYPE>`
- `/show`
- `/doc`
- `/revise <section> [instruction]`
- `/clear <slot>`
- `/draft`
- `/lint`
- `/repair`
- `/export`
- `/reset`
- `/paste`

### `hpa chat`

作为一个 OpenAI-compatible 的原始聊天 CLI：

```bash
hpa chat --base-url http://127.0.0.1:8080 --model <model>
```

### `hpa web`

启动本地网页交互界面。页面会复用同一套 `ClarificationService`，左侧是对话和选择题，右侧是共享 prompt 文档与 facts 面板。

```bash
hpa web --host 127.0.0.1 --port 7860
```

## 架构

项目采用四层结构：

- `src/hpa/domain`
  - 核心领域对象，如 `TemplateSpec`、`PromptSpec`、`SessionState`
- `src/hpa/application`
  - 业务编排，如 mode 解析、slot 补全、追问、compose、validate、repair
- `src/hpa/infrastructure`
  - YAML 配置、模板仓库、导出器、LangChain LLM 适配
- `src/hpa/interfaces`
  - CLI 与本地 Web 入口

## 配置

- 模板配置：`configs/templates.yaml`
- agent 配置：`configs/agent.yaml`
- LLM 配置：`configs/llm.yaml`

LLM 配置优先级：

1. CLI 参数
2. 环境变量
3. YAML 配置
4. 默认值

环境变量：

- `HPA_LLM_BASE_URL`
- `HPA_LLM_API_KEY`
- `HPA_LLM_MODEL`
- `HPA_LLM_TIMEOUT_SEC`
- `HPA_LLM_TEMPERATURE`
- `HPA_LLM_MAX_TOKENS`

## 开发安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

## 设计边界

- 不做重型 autonomous coding agent
- 不让 tool calling 成为默认中心
- LLM 可以建议，但不能偷偷改写已确认事实
- skills / capabilities 目前只保留插件接口，默认关闭
- 交互上优先走“选择题”，只有必要时才让用户补自由文本
