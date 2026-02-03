from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from hpa.checklist import missing_slots
from hpa.composer import compose_prompt
from hpa.config import TemplatesConfig
from hpa.extractor import apply_user_message_to_slots
from hpa.state import AgentState

from .agent_config import AgentAssistConfig
from .llm_questioner import generate_questions
from .llm_refiner import refine_prompt
from .llm_slot_extractor import extract_slots


@dataclass
class StepResult:
    text: str
    done: bool = False


class LLMAssistedAgentEngine:
    def __init__(
        self,
        templates_cfg: TemplatesConfig,
        assist_cfg: AgentAssistConfig,
        client,
    ) -> None:
        self.cfg = templates_cfg
        self.assist_cfg = assist_cfg
        self.client = client
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
                    "- /clear <slot> 清空单个槽位\n"
                    "- /export 导出当前会话 JSON\n"
                    "- /reset 重置\n"
                    "- /paste 进入多行粘贴模式（CLI）\n"
                    "\n"
                    "提示：支持 JSON / key:value 或 key=value 直接填槽位。"
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
            if not self.state.mode_key():
                return StepResult(text="当前未选择模式。请先使用 /mode 选择模板。")
            mode_key = self.state.mode_key()
            required = self.cfg.required_slots.get(mode_key, [])
            filled = {k for k, v in self.state.slots.items() if str(v).strip()}
            req_lines = [f"- {s}: {filled if s in filled else missing}" for s in required]

            all_slots = list(self.state.slots.keys())
            ordered: list[str] = []
            seen: set[str] = set()
            for key in self.cfg.slot_priority:
                if key in all_slots and key not in seen:
                    ordered.append(key)
                    seen.add(key)
            for key in sorted(all_slots):
                if key not in seen:
                    ordered.append(key)
                    seen.add(key)
            slot_lines = [f"- {k}: {self.state.slots.get(k, )}" for k in ordered] or ["- (none)"]

            lines = [
                f"模式：{mode_key}",
                "必填槽位状态：",
                *req_lines,
                "当前槽位：",
                *slot_lines,
            ]
            return StepResult(text="\n".join(lines))

        if cmd.startswith("/clear"):
            parts = cmd.split(maxsplit=1)
            if len(parts) != 2:
                return StepResult(text="用法：/clear <slot>")
            slot = self.cfg.normalize_key(parts[1])
            if slot in self.state.slots:
                self.state.slots.pop(slot, None)
                if self.state.last_asked_slot == slot:
                    self.state.last_asked_slot = None
                return StepResult(text=f"已清除槽位：{slot}")
            return StepResult(text=f"未找到槽位：{slot}")

        if cmd == "/export":
            if not self.state.mode_key():
                return StepResult(text="请先选择模式后再导出。")
            export_dir = Path("exports")
            export_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = export_dir / f"session_{timestamp}.json"
            prompt = compose_prompt(self.state, self.cfg)
            if self.assist_cfg.enable_llm_refiner:
                prompt = refine_prompt(self.client, prompt, strict_json_only=self.assist_cfg.strict_json_only)
            payload = {
                "mode": self.state.mode_key(),
                "slots": self.state.slots,
                "final_prompt": prompt,
                "created_at": datetime.now().isoformat(),
            }
            out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return StepResult(text=f"已导出：{out_path}")

        if cmd == "/reset":
            return self.reset()

        if cmd == "/paste":
            return StepResult(text="粘贴模式由 CLI 处理，请直接在 CLI 使用 /paste。")

        return None

    def _maybe_llm_extract(self, user_text: str, rule_updated: set[str], missing: list[str], filled_freeform: bool) -> None:
        if not self.assist_cfg.enable_llm_extractor:
            return
        should_call = (not rule_updated) or len(missing) >= 2
        if not should_call:
            return

        updates = extract_slots(
            self.client,
            self.cfg,
            self.state,
            user_text,
            strict_json_only=self.assist_cfg.strict_json_only,
        )
        if not updates:
            return

        explicit_updates = rule_updated if not filled_freeform else set()
        for key, value in updates.items():
            if self.assist_cfg.fill_only_empty_slots:
                if not self.state.slots.get(key, "").strip() or key in explicit_updates:
                    self.state.slots[key] = value
            else:
                self.state.slots[key] = value

    def _build_question_text(self, questions: list[dict[str, str]]) -> str:
        lines = ["为生成可用 prompt，还缺关键信息："]
        for item in questions:
            lines.append(item["question"])
        return "\n".join(lines)

    def step(self, user_text: str) -> StepResult:
        self.state.turn += 1
        self.state.history.append(("user", user_text))

        cmd_res = self._handle_command(user_text)
        if cmd_res is not None:
            return cmd_res

        if not self.state.mode_key():
            return StepResult(text=self.cfg.mode_menu_text(), done=False)

        rule_result = apply_user_message_to_slots(self.state, user_text)
        rule_updated = set(rule_result.get("updated", []))
        filled_freeform = bool(rule_result.get("filled_freeform"))

        missing = missing_slots(self.state, self.cfg)
        self._maybe_llm_extract(user_text, rule_updated, missing, filled_freeform)
        missing = missing_slots(self.state, self.cfg)

        if missing:
            if self.assist_cfg.enable_llm_questioner:
                questions = generate_questions(
                    self.client,
                    self.cfg,
                    self.state,
                    missing,
                    strict_json_only=self.assist_cfg.strict_json_only,
                )
                if questions:
                    selected = questions[: self.assist_cfg.max_questions_per_turn]
                    self.state.last_asked_slot = selected[0]["slot"]
                    return StepResult(text=self._build_question_text(selected), done=False)

            if self.assist_cfg.question_fallback_to_bank:
                slot = missing[0]
                self.state.last_asked_slot = slot
                q = self.cfg.questions.get(slot, f"请补充：{slot}")
                return StepResult(text="为生成可用 prompt，还缺一项关键信息：\n" + q, done=False)

        prompt = compose_prompt(self.state, self.cfg)
        if self.assist_cfg.enable_llm_refiner:
            prompt = refine_prompt(self.client, prompt, strict_json_only=self.assist_cfg.strict_json_only)
        return StepResult(text="信息已足够，下面是可直接使用的最终 prompt：\n\n" + prompt, done=True)
