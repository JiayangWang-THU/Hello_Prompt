from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from .config import TemplatesConfig
from .state import AgentState
from .extractor import apply_user_message_to_slots
from .checklist import missing_slots
from .composer import compose_prompt


@dataclass
class StepResult:
    text: str
    done: bool = False


class AgentEngine:
    """Manual-template agent engine (no LLM routing).
    - User must choose a mode via `/mode CATEGORY SUBTYPE`
    - The engine asks for missing required slots in priority order
    - Once filled, it composes a final prompt
    """

    def __init__(self, cfg_path: str | Path = "configs/templates.json"):
        self.cfg = TemplatesConfig.load(cfg_path)
        self.state = AgentState()

    def reset(self) -> StepResult:
        self.state = AgentState()
        return StepResult(text="已重置。\n" + self.cfg.mode_menu_text(), done=False)

    def _handle_command(self, user_text: str) -> Optional[StepResult]:
        cmd = user_text.strip()

        if cmd == "/help":
            return StepResult(
                text=(
                    "命令：\n"
                    "- /templates 显示模板\n"
                    "- /mode <CATEGORY> <SUBTYPE> 选择模板（必须先选）\n"
                    "- /show 查看当前slots\n"
                    "- /reset 重置\n"
                    "\n"
                    "提示：支持 key:value 或 key=value 直接填槽位，例如：\n"
                    "runtime_env: Ubuntu 22.04\n"
                    "language: Python"
                )
            )

        if cmd == "/templates":
            return StepResult(text=self.cfg.mode_menu_text())

        if cmd.startswith("/mode"):
            parts = cmd.split()
            if len(parts) != 3:
                return StepResult(text="用法：/mode <CATEGORY> <SUBTYPE>，例如：/mode CODE EXTEND")
            _, cat, sub = parts
            cat, sub = cat.upper(), sub.upper()
            if (cat, sub) not in self.cfg.allowed_modes():
                return StepResult(
                    text=(
                        f"不支持的模式：{cat}/{sub}\n"
                        "请用 /templates 查看可选模板。"
                    )
                )
            self.state.category = cat
            self.state.subtype = sub
            self.state.last_asked_slot = None
            return StepResult(text=f"模式已设定为 {cat}/{sub}。请先填写 goal（可直接输入：goal: ...）。")

        if cmd == "/show":
            return StepResult(text=f"当前状态：mode={self.state.mode_key()}, slots={self.state.slots}")

        if cmd == "/reset":
            return self.reset()

        return None

    def step(self, user_text: str) -> StepResult:
        self.state.turn += 1
        self.state.history.append(("user", user_text))

        # Commands first
        cmd_res = self._handle_command(user_text)
        if cmd_res is not None:
            return cmd_res

        # Must choose mode first
        if not self.state.mode_key():
            return StepResult(text=self.cfg.mode_menu_text(), done=False)

        # Fill slots
        apply_user_message_to_slots(self.state, user_text)

        # Ask next missing slot
        miss = missing_slots(self.state, self.cfg)
        if miss:
            slot = miss[0]
            self.state.last_asked_slot = slot
            q = self.cfg.questions.get(slot, f"请补充：{slot}")
            return StepResult(text="为生成可用 prompt，还缺一项关键信息：\n" + q, done=False)

        # Compose final prompt
        return StepResult(text="信息已足够，下面是可直接使用的最终 prompt：\n\n" + compose_prompt(self.state), done=True)
