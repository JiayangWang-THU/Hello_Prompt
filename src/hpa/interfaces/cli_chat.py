from __future__ import annotations

import argparse
from typing import Any

from hpa.infrastructure import load_llm_config
from hpa.infrastructure.llm import LegacyChatClient, build_langchain_chat_model


def run_chat(args: argparse.Namespace) -> None:
    overrides = {
        "base_url": args.base_url,
        "api_key": args.api_key,
        "model": args.model,
        "timeout_sec": args.timeout_sec,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
    }
    cfg = load_llm_config(args.config, overrides)
    system_prompt = args.system or "You are a helpful assistant."
    messages = [{"role": "system", "content": system_prompt}]

    try:
        model = build_langchain_chat_model(cfg)
        use_langchain = True
    except Exception:  # noqa: BLE001
        model = LegacyChatClient(cfg)
        use_langchain = False

    print("HPA Chat (OpenAI-compatible)")
    print(
        "LLM 配置："
        f" base_url={cfg.base_url},"
        f" model={cfg.model},"
        f" timeout={cfg.timeout_sec}s,"
        f" temperature={cfg.temperature},"
        f" max_tokens={cfg.max_tokens}"
    )
    if not use_langchain:
        print("Warning: langchain-openai 不可用，已使用 legacy chat client。")
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
            print(
                "LLM 配置："
                f" base_url={cfg.base_url},"
                f" model={cfg.model},"
                f" timeout={cfg.timeout_sec}s,"
                f" temperature={cfg.temperature},"
                f" max_tokens={cfg.max_tokens}"
            )
            continue
        if user.startswith("/system"):
            new_system = user[len("/system") :].strip()
            if not new_system:
                print("用法：/system <text>")
            else:
                system_prompt = new_system
                messages[0]["content"] = system_prompt
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
            reply = _chat_once(model, messages, use_langchain=use_langchain)
        except Exception as exc:  # noqa: BLE001
            messages.pop()
            print(f"请求失败：{exc}")
            continue

        print("\nAssistant>")
        print(reply)
        print("-" * 72)
        messages.append({"role": "assistant", "content": reply})


def _chat_once(model, messages: list[dict[str, Any]], use_langchain: bool) -> str:
    if use_langchain:
        response = model.invoke(messages)
        content = getattr(response, "content", response)
        if isinstance(content, list):
            return "".join(str(item) for item in content)
        return str(content)
    return model.chat(messages)


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
