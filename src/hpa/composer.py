from __future__ import annotations

from .state import AgentState


def compose_prompt(state: AgentState) -> str:
    """Default prompt composer (works for CODE/* templates).
    You can later implement per-mode composers or a renderer layer.
    """
    s = state.slots
    lines: list[str] = []
    lines.append("你将扮演：资深软件工程师 + 提示词工程师。")
    lines.append("")
    lines.append("【任务类型】")
    lines.append(f"- category: {state.category}")
    lines.append(f"- subtype: {state.subtype}")
    lines.append("")
    lines.append("【目标】")
    lines.append(f"- {s.get('goal','')}")
    lines.append("")
    lines.append("【背景/约束】")
    for k in ["base_system", "repo_context", "new_features", "compatibility",
              "language", "runtime_env", "scope", "interfaces"]:
        if k in s and s[k].strip():
            lines.append(f"- {k}: {s[k]}")
    lines.append("")
    lines.append("【交付物与验收】")
    for k in ["deliverable", "review_focus", "acceptance_tests"]:
        if k in s and s[k].strip():
            lines.append(f"- {k}: {s[k]}")
    lines.append("")
    lines.append("【输出格式】")
    lines.append(s.get("output_format", "Markdown（含清晰标题与列表）"))
    lines.append("")
    lines.append("【额外要求】")
    lines.append("- 如果信息不足，先列出缺失清单并给出你需要我补充的最少问题（<=3个）。")
    lines.append("- 先给总体方案，再给可复制粘贴的关键代码/命令/目录结构示例。")
    return "\n".join(lines)
