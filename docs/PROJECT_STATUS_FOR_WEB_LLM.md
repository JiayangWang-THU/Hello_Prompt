# 项目现状摘要（给网页端 LLM）

更新时间：2026-03-01

## 1. 项目现在是什么

这是一个名为 **Hello Prompt Agent / hello-prompt-agent** 的 Python CLI 项目。  
它不是重型 autonomous agent，而是一个 **CLI-first 的 Prompt Clarification Framework**：

- 用户先给出模糊需求种子
- 系统逐步识别 mode、补全 facts、提出建议
- 最终输出结构化、高质量 prompt

它的核心定位仍然是：

> 需求澄清 + Prompt 生长/组装，而不是全自动代码代理。

## 2. 重构后的架构

项目现在采用四层架构：

### Domain

纯业务模型，不依赖 LangChain：

- `TemplateSpec`
- `SlotDefinition`
- `PromptSpec`
- `SessionState`
- `ClarificationQuestion`
- `Suggestion`
- `ValidationIssue`
- `ComposerResult`

### Application

业务编排层：

- `ClarificationService`
- `ModeResolverService`
- `SlotFillingService`
- `QuestionPlanningService`
- `PromptCompositionService`
- `ValidationService`
- `RepairService`
- `SessionService`

### Infrastructure

外部依赖适配层：

- YAML / JSON 模板加载
- JSON 导出
- LangChain LLM enhancer
- OpenAI-compatible LLM 配置
- disabled capability / skill provider

### Interface

CLI 层：

- `hpa agent`
- `hpa chat`

## 3. LangChain 的角色

项目现在已经把 LLM 增强链路统一到了 LangChain 风格的轻量编排上，核心使用方式是：

- `ChatPromptTemplate`
- 可组合的 `Runnable` pipeline
- Pydantic 结构化输出解析

当前已设计为可插拔链的能力包括：

- slot extraction chain
- question generation chain
- mode routing chain
- prompt refinement chain
- validation-repair chain

但系统仍坚持：

- LLM 负责主交互编排，但不是事实裁决者
- 已确认事实不能被 LLM 偷偷改写

## 4. 当前产品边界

网页端 LLM 不应把这个项目理解成：

- 通用 autonomous coding agent
- Web 应用
- 多工具编排中心
- 带数据库或长期记忆的系统

它应该被理解成：

- 本地 Python 包
- 以 CLI 为核心的交互系统
- 以模板和 slots 为骨架的需求澄清器
- 把模糊意图“生长”为高质量 prompt 的系统

## 5. 目前支持的能力

### `hpa agent`

统一的澄清主引擎，规则版已经去掉，交互改为 LLM 选择题优先。

保留命令：

- `/mode`
- `/show`
- `/clear`
- `/export`
- `/help`

新增命令：

- `/doc`
- `/revise`
- `/draft`
- `/lint`
- `/repair`

### `hpa chat`

原始 OpenAI-compatible chat CLI，优先走 `langchain-openai`，不可用时回退到 legacy HTTP client。

## 6. 当前支持的模式

仍然只支持 3 类 `CODE/*` 模式：

- `CODE/FROM_SCRATCH`
- `CODE/REVIEW`
- `CODE/EXTEND`

模板继续由 `configs/templates.yaml` 驱动，但现在配置更结构化，带有：

- slot definitions
- aliases
- required slots
- slot order
- deliverable defaults
- acceptance defaults

## 7. 事实层与建议层

这是当前实现里非常重要的边界：

- **事实层**：`SessionState.confirmed_slots`
- **建议层**：`SessionState.suggestions`

LLM 从用户当轮输入里“提取到的事实”才会进入事实层。  
LLM 主动提出的候选答案、补问建议、修复建议都进入建议层或选择题层，不直接覆盖事实层。

## 8. 当前已补齐的关键问题

重构后已经解决这些旧问题：

- 不再有手动模式和 assisted 模式的重复引擎
- 规则版主路径已经去掉
- `/show` 不再依赖旧 assisted engine，因此原先的 `missing` 未定义 bug 已被消除
- README / 架构文档 / 使用文档已对齐新实现
- 旧 `src/agent` 实验实现已移除，避免双轨代码继续混淆

## 9. 当前仍然没有的能力

即使完成重构，项目仍然**没有**：

- Web UI
- HTTP API
- 数据库持久化
- 长期记忆
- 默认启用的工具调用系统
- 重型 plan-act-reflect 自主代理框架
- 以 skills 为中心的执行架构

skills / capability 目前只保留了轻量插件接口，默认关闭。

## 10. 测试现状

当前测试重点覆盖：

- 手动基本流程
- assisted 基本流程
- `/show`、`/clear`、`/export`
- alias 与 `last_asked_slot`
- validation 对缺失 section / facts 的发现
- repair 在 LLM 关闭时的 graceful fallback
- mode routing suggestion 不覆盖用户手动 mode
- composer 基于 `PromptSpec` 的结构化输出

测试使用 fake LLM enhancer，不依赖真实联网模型。

## 11. 可直接复制给网页端 LLM 的上下文

```text
这是一个名为 Hello Prompt Agent 的 Python CLI 项目。它不是通用 autonomous agent，也不是 Web 服务。它的核心目标是把用户的模糊需求逐步澄清成结构化、高质量 prompt，供 Codex 或其他代码 LLM 使用。

当前项目已经完成一次面向 LangChain 的架构重构，但产品边界没有改变：它仍然是一个“需求澄清 + Prompt 生长/组装”系统，而不是全自动 coding agent。

当前架构分四层：
1. Domain：纯业务模型，如 TemplateSpec、PromptSpec、SessionState、Suggestion、ValidationIssue
2. Application：业务编排，如 ClarificationService、ModeResolverService、SlotFillingService、QuestionPlanningService、PromptCompositionService、ValidationService、RepairService
3. Infrastructure：模板仓库、导出器、LLM 配置、LangChain enhancer
4. Interface：CLI（hpa agent / hpa chat）

LangChain 在这个项目中是“轻量 orchestration 核心”，主要用于：
- slot extraction chain
- question generation chain
- mode routing chain
- prompt refinement chain
- validation-repair chain

但系统仍坚持：
- LLM 主导交互，但不是事实裁决者
- 已确认事实不能被 LLM 偷偷改写
- 事实层和建议层必须分离

当前支持的 mode 仍然只有三类：
- CODE/FROM_SCRATCH
- CODE/REVIEW
- CODE/EXTEND

CLI 仍然是主入口：
- hpa agent
- hpa chat

agent 命令包括：
- /mode
- /show
- /doc
- /revise
- /clear
- /draft
- /lint
- /repair
- /export

当前没有：
- Web UI
- HTTP API
- 数据库
- 长期记忆
- 默认开启的工具调用系统
- 重型 autonomous agent 框架

如果你要帮助这个项目，请把它理解成：
一个本地 CLI 版 prompt clarification framework，它通过模板和槽位收集事实，通过建议层引导用户补全结构，最终输出高质量 prompt。
```
