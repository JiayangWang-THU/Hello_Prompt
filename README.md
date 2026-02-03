# Hello Prompt Agent Framework (Manual Template Mode)

这是一个“可控工作流”式的 agent 框架：先手动选择模板（模式），再按必填字段（slots）逐步追问，直到生成最终可用 prompt。

## 安装（本地开发）
```bash
cd hello_prompt_agent_framework
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

## 运行
```bash
hpa
```

## 交互命令
- `/templates`：列出可用模板
- `/mode CODE EXTEND`：选择模板（必须先选）
- `/show`：查看当前 slots
- `/reset`：重置会话
- 支持 `key: value` 或 `key=value` 直接填槽位

## 配置扩展
所有模板/必填字段/追问句子都在 `configs/templates.json`：
- 增加新模板：在 `modes` 里加一项，并在 `required_slots` 添加对应键
- 新字段：在 `questions` 里加追问文本
