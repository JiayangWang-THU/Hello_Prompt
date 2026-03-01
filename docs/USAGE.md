# Usage

## CLI Quickstart

1. `hpa agent`
2. 直接描述你的任务
3. 根据系统给出的数字选项完成 mode 和关键槽位选择
4. 必要时补一小段自由文本
5. 用 `/doc`、`/draft`、`/lint`、`/repair` 调整共享 prompt 文档
6. 用 `/export` 保存当前会话 JSON

## Commands

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

## Interaction Style

`hpa agent` 现在默认就是 LLM 驱动：

- 优先给 mode 选择题
- 优先给关键槽位候选答案
- 用户输入数字即可推进
- 只有候选答案都不合适时，才补一小段自由文本
