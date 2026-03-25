# Hello Prompt Agent

Hello Prompt Agent 是一个面向网页端大模型的需求收敛系统。  
它通过持续对话，把用户最初模糊、不完整、甚至自我矛盾的想法，逐轮收敛成更具体、更可执行的 prompt。

## 项目定位

- Python 包，主入口是 CLI
- 面向代码大模型的多轮需求收敛
- 系统主动生成若干高概率猜测，而不是等用户先把需求说清楚
- 每轮只推进当前最值得确认的一步
- 明确区分事实层和建议层
- LLM 可以猜测、建议、改写，但不能静默篡改已确认事实
- 支持收敛、compose、lint、repair、document revise 的完整闭环

## 核心方法

这个项目不想做成 prompt 填表器。

它的工作方式是：

- 用户先给出一个模糊任务
- 系统根据当前上下文猜测用户更可能真正想要的几个方向
- 系统给出 top-k 建议，帮助用户快速选择、修正或补充
- 每一轮只推进一步，反复小规划，而不是一次性全局规划
- 当信息足够稳定时，再把收敛结果整理成共享 prompt 文档

可以把它理解成：

- 多次规划，单步执行
- 猜测优先，修正友好
- 用户共创，而不是表单填写

## 当前入口

### `hpa agent`

主工作流。用户输入任务种子后，系统会先判断 mode，并持续给出 top-k 收敛建议，帮助用户把真实意图说清楚。

```bash
hpa agent
```

支持命令：

- `/help`
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

原始 OpenAI-compatible chat CLI，不走需求收敛工作流。

```bash
hpa chat --base-url http://127.0.0.1:8080 --model <model>
```

### `hpa web`

本地 Web 界面，复用同一套 `ClarificationService`。当前实现适合本机单用户调试，可作为网页端大模型交互的本地入口，不是面向多用户部署的 Web 服务。

```bash
hpa web --host 127.0.0.1 --port 7860
```

## 项目结构

- `src/hpa/domain`
  - 领域模型，定义模板、会话状态、候选建议、共享文档、校验问题等
- `src/hpa/application`
  - 工作流编排，处理 mode、意图猜测、收敛推进、compose、validate、repair
- `src/hpa/infrastructure`
  - 配置加载、模板仓库、导出器、LLM 适配、可选能力提供者
- `src/hpa/interfaces`
  - CLI 和本地 Web 入口
- `src/hpa/webapp`
  - Web UI 静态资源
- `configs`
  - 模板、agent 行为和 LLM 配置
- `tests`
  - 基于 fake LLM 的单元测试

## 配置

- 模板：`configs/templates.yaml`
- agent：`configs/agent.yaml`
- LLM：`configs/llm.yaml`

LLM 配置优先级：

1. CLI 参数
2. 环境变量
3. YAML 配置
4. 默认值

支持的环境变量：

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

如果要运行测试，还需要额外安装 `pytest`。

## 设计边界

- 不做重型 autonomous coding agent
- 不默认围绕 tool calling 展开
- 不提供数据库、长期记忆或多用户服务端能力
- 不把用户交互设计成“逐字段填表”
- 已确认事实不能被 LLM 静默覆盖
- capability / skill 接口默认关闭，仅保留扩展点
