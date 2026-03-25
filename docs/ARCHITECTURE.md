# Architecture

## Product Boundary

Hello Prompt Agent 是一个面向网页端大模型的需求收敛系统。

- 它不是通用 autonomous coding agent
- 它不是默认以 tool calling 为中心的平台
- 它的职责是通过持续对话收敛用户真实意图，再生成结构化 prompt
- 它不是一个让用户逐字段填写的 prompt 表单器

## Core Design

项目围绕两个核心约束展开：

1. 事实层和建议层分离
2. 多次规划，单步执行

事实层保存在 `SessionState.confirmed_slots`。  
建议层保存在 `SessionState.suggestions`。  
LLM 可以提出候选猜测、问题和改写建议，但不能绕过用户确认去覆盖事实层。

系统每一轮都只做一件最值钱的事：

- 判断当前最该收敛的焦点
- 生成 top-k 假设建议
- 让用户选择、修正或补充
- 将确认后的结果沉淀为 facts

因此，内部虽然仍保留模板和 slots 作为结构化骨架，但用户感知到的核心交互应该是“猜测与收敛”，而不是“填表与补槽”。

## Layers

### Domain

`src/hpa/domain` 只放纯业务模型，不依赖 LangChain 或 CLI。

核心对象：

- `TemplateSpec`
- `SlotDefinition`
- `PromptSpec`
- `SharedPromptDocument`
- `SessionState`
- `ChoicePrompt`
- `Suggestion`
- `ValidationIssue`
- `ComposerResult`

这一层定义“系统在处理什么”，不定义“怎么交互”。

### Application

`src/hpa/application` 负责工作流编排，是项目的核心。

- `ClarificationService`
  - 统一对外工作流，串起 mode 判断、需求收敛、draft、lint、repair、revise
- `ModeResolverService`
  - 管理 mode 设置和 mode 推荐
- `SlotFillingService`
  - 将用户确认过的表达沉淀为结构化 facts
- `ConvergencePlanningService`
  - 决定当前最值得推进的一步，并生成 top-k 收敛建议
- `PromptCompositionService`
  - 从已确认事实生成 `PromptSpec`、共享文档和最终 prompt
- `ValidationService`
  - 校验结构完整性和事实保留情况
- `RepairService`
  - 在需要时尝试修复文档
- `SessionService`
  - 负责 show、clear、export 等会话辅助逻辑

### Infrastructure

`src/hpa/infrastructure` 负责与外部配置和依赖打交道。

- `TemplateRepository`
  - 加载 `configs/templates.yaml`
- `config_loader`
  - 加载 agent 和 LLM 配置
- `llm/*`
  - LangChain 模型接入、prompt、parser、chain 组装
- `SessionExporter`
  - 导出当前会话
- `DisabledCapabilityProvider`
  - 默认关闭的 capability 接口

### Interfaces

入口层分成两部分：

- `src/hpa/cli.py`
  - 顶层命令分发
- `src/hpa/interfaces/cli_agent.py`
  - 澄清工作流的 CLI 入口
- `src/hpa/interfaces/cli_chat.py`
  - 原始聊天 CLI
- `src/hpa/interfaces/web_app.py`
  - 本地 Web UI 入口和最小 HTTP handler

`src/hpa/webapp` 提供 Web UI 的静态资源。

## Runtime Flow

### `hpa agent`

1. 用户输入任务种子
2. 系统确定或推荐 mode
3. 系统判断这一轮最值得收敛的焦点
4. 系统生成 top-k 猜测建议
5. 用户选择、修正或补充
6. 事实写入 `confirmed_slots`
7. 生成 `PromptSpec` 和共享文档
8. 运行 lint，必要时 repair 或 revise

### `hpa web`

- 复用同一套 `ClarificationService`
- 通过 snapshot 暴露当前 mode、slots、document、history、issues
- 当前更接近本地单会话调试界面，不是多用户 Web 服务

## Code Organization Notes

- `domain` 保持纯净是这个项目可维护性的关键
- `application` 是主要演进面，新增能力应优先围绕“收敛策略”切分职责
- `interfaces` 应尽量薄，只负责输入输出和状态呈现
- `infrastructure` 应只做适配，不应反向侵入业务规则
