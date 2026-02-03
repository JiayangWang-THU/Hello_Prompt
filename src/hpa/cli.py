from __future__ import annotations

import argparse
from pathlib import Path

from .engine import AgentEngine


def main():
    parser = argparse.ArgumentParser(description="Hello Prompt Agent (manual template mode)")
    parser.add_argument("--config", type=str, default="configs/templates.json", help="path to templates.json")
    args = parser.parse_args()

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
            user = "\n".join(lines)
            if not user.strip():
                print("（空输入，已取消）")
                continue
        res = engine.step(user)
        print("\nAgent>")
        print(res.text)
        print("-" * 72)
        if res.done:
            print("（已生成最终 prompt。你可以继续补充以迭代，或 /reset 开新任务。）")
            print("-" * 72)
