# Usage

## Quick Start

### Clarification Workflow

```bash
hpa agent
```

典型流程：

1. 输入一句任务描述
2. 系统先猜测最接近的 mode
3. 系统给出 top-k 收敛建议
4. 你可以直接选择，也可以修正它的猜测
5. 用 `/draft` 查看当前共享文档
6. 用 `/lint`、`/repair`、`/revise` 继续调整
7. 用 `/export` 导出会话

### Raw Chat

```bash
hpa chat --base-url http://127.0.0.1:8080 --model <model>
```

### Local Web UI

```bash
hpa web --host 127.0.0.1 --port 7860
```

## Agent Commands

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

## Interaction Rules

- 优先使用数字选择推进流程
- mode 未确定前，系统会先给 mode 候选
- 系统会主动猜测你可能真正想要的方向，而不是等你自己先讲清楚
- 每一轮只推进一个最值得确认的点
- 如果系统猜错了，直接输入文字修正即可
- `/doc` 查看的是共享文档视图，不只是原始 facts

## Current Modes

- `CODE/FROM_SCRATCH`
- `CODE/REVIEW`
- `CODE/EXTEND`
