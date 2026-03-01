from __future__ import annotations

import argparse
import sys

from hpa.interfaces import run_agent, run_chat


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hello Prompt Agent Framework")
    subparsers = parser.add_subparsers(dest="command")

    agent_parser = subparsers.add_parser("agent", help="prompt clarification agent")
    agent_parser.add_argument("--config", type=str, default="configs/templates.yaml", help="path to templates config")
    agent_parser.add_argument("--agent-config", type=str, default="configs/agent.yaml", help="path to agent config")
    agent_parser.add_argument("--llm-config", type=str, default="configs/llm.yaml", help="path to llm config")
    agent_parser.set_defaults(func=run_agent)

    chat_parser = subparsers.add_parser("chat", help="raw LLM chat (OpenAI-compatible)")
    chat_parser.add_argument("--config", type=str, default="configs/llm.yaml", help="path to llm config")
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
        args.func(args)
        return
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
