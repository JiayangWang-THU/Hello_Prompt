from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent.agent_config import load_agent_config
from agent.llm_agent_engine import LLMAssistedAgentEngine
from hpa.config import TemplatesConfig

from .engine import AgentEngine
from .llm_client import OpenAICompatibleChatClient
from .llm_config import LLMConfig, load_llm_config


def _read_paste() -> str | None:
    print("进入粘贴模式，单行输入 . 结束：")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except (KeyboardInterrupt, EOFError):
            line = "."
        if line.strip() == ".":
            break
        lines.append(line)
    text = "\n".join(lines).strip()
    return text if text else None


def _print_llm_summary(cfg: LLMConfig) -> None:
    print(
        "LLM 配置："
        f" base_url={cfg.base_url},"
        f" model={cfg.model},"
        f" timeout={cfg.timeout_sec}s,"
        f" temperature={cfg.temperature},"
        f" max_tokens={cfg.max_tokens}"
    )


def init_assisted_agent_engine(
    templates_path: str | Path,
    agent_config_path: str | Path,
    llm_config_path: str | Path,
) -> LLMAssistedAgentEngine:
    templates_cfg = TemplatesConfig.load(templates_path)
    assist_cfg = load_agent_config(agent_config_path)
    llm_cfg = load_llm_config(llm_config_path, {})
    client = OpenAICompatibleChatClient(llm_cfg)
    return LLMAssistedAgentEngine(templates_cfg, assist_cfg, client)


def run_agent(args: argparse.Namespace) -> None:
    if args.assist_llm:
        engine = init_assisted_agent_engine(args.config, args.agent_config, args.llm_config)
        print("Hello Prompt Agent Framework (LLM-assisted)")
    else:
        engine = AgentEngine(cfg_path=Path(args.config))
        print("Hello Prompt Agent Framework (Manual Template Mode)")
    print("先输入 /templates 查看模板，或直接 /mode CODE EXTEND")
    print("输入 /help 查看命令说明。")
    print("-" * 72)

    while True:
        try:
            user = input("You> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n退出。")
            break
        if not user:
            continue
        if user == "/paste":
            pasted = _read_paste()
            if not pasted:
                print("（空输入，已取消）")
                continue
            user = pasted
        res = engine.step(user)
        print("\nAgent>")
        print(res.text)
        print("-" * 72)
        if res.done:
            print("（已生成最终 prompt。你可以继续补充以迭代，或 /reset 开新任务。）")
            print("-" * 72)


def init_chat_client(config_path: str | Path, cli_overrides: dict) -> tuple[LLMConfig, OpenAICompatibleChatClient]:
    cfg = load_llm_config(config_path, cli_overrides)
    client = OpenAICompatibleChatClient(cfg)
    return cfg, client


def run_chat(args: argparse.Namespace) -> None:
    overrides = {
        "base_url": args.base_url,
        "api_key": args.api_key,
        "model": args.model,
        "timeout_sec": args.timeout_sec,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
    }
    cfg, client = init_chat_client(args.config, overrides)
    system_prompt = args.system or "You are a helpful assistant."
    messages = [{"role": "system", "content": system_prompt}]

    print("HPA Chat (OpenAI-compatible)")
    _print_llm_summary(cfg)
    print("命令：/exit 退出 | /config 查看配置 | /system <text> 设置system | /clear 清空历史 | /paste 多行")
    print("-" * 72)

    while True:
        try:
            user = input("You> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n退出。")
            break
        if not user:
            continue

        if user == "/exit":
            print("退出。")
            break
        if user == "/config":
            _print_llm_summary(cfg)
            continue
        if user.startswith("/system"):
            new_system = user[len("/system"):].strip()
            if not new_system:
                print("用法：/system <text>")
            else:
                system_prompt = new_system
                if messages and messages[0].get("role") == "system":
                    messages[0]["content"] = system_prompt
                else:
                    messages.insert(0, {"role": "system", "content": system_prompt})
                print("System prompt 已更新。")
            continue
        if user == "/clear":
            messages = [{"role": "system", "content": system_prompt}]
            print("已清空历史（保留 system）。")
            continue
        if user == "/paste":
            pasted = _read_paste()
            if not pasted:
                print("（空输入，已取消）")
                continue
            user_text = pasted
        else:
            user_text = user

        messages.append({"role": "user", "content": user_text})
        try:
            reply = client.chat(messages)
        except Exception as exc:  # noqa: BLE001
            messages.pop()
            print(f"请求失败：{exc}")
            continue

        print("\nAssistant>")
        print(reply)
        print("-" * 72)
        messages.append({"role": "assistant", "content": reply})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hello Prompt Agent Framework")
    subparsers = parser.add_subparsers(dest="command")

    agent_parser = subparsers.add_parser("agent", help="manual template agent")
    agent_parser.add_argument(
        "--config",
        type=str,
        default="configs/templates.yaml",
        help="path to templates.yaml",
    )
    agent_parser.add_argument("--assist-llm", action="store_true", help="enable LLM-assisted workflow")
    agent_parser.add_argument(
        "--agent-config",
        type=str,
        default="configs/agent.yaml",
        help="path to agent.yaml",
    )
    agent_parser.add_argument(
        "--llm-config",
        type=str,
        default="configs/llm.yaml",
        help="path to llm.yaml",
    )
    agent_parser.set_defaults(func=run_agent)

    chat_parser = subparsers.add_parser("chat", help="raw LLM chat (OpenAI-compatible)")
    chat_parser.add_argument("--config", type=str, default="configs/llm.yaml", help="path to llm.yaml")
    chat_parser.add_argument("--base-url", type=str, default=None)
    chat_parser.add_argument("--api-key", type=str, default=None)
    chat_parser.add_argument("--model", type=str, default=None)
    chat_parser.add_argument("--timeout-sec", type=int, default=None)
    chat_parser.add_argument("--temperature", type=float, default=None)
    chat_parser.add_argument("--max-tokens", type=int, default=None)
    chat_parser.add_argument("--system", type=str, default="You are a helpful assistant.")
    chat_parser.set_defaults(func=run_chat)

    return parser


def main() -> None:
    parser = build_parser()
    if len(sys.argv) == 1:
        args = parser.parse_args(["agent"])
        run_agent(args)
        return
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)
