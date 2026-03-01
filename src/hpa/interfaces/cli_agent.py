from __future__ import annotations

import argparse
from pathlib import Path

from hpa.application import (
    ClarificationService,
    ModeResolverService,
    PromptCompositionService,
    QuestionPlanningService,
    RepairService,
    SessionService,
    SlotFillingService,
    ValidationService,
)
from hpa.infrastructure import (
    DisabledCapabilityProvider,
    SessionExporter,
    TemplateRepository,
    load_agent_config,
    load_llm_config,
)
from hpa.infrastructure.llm import LangChainLLMEnhancer, build_langchain_chat_model


def build_clarification_service(
    templates_path: str | Path,
    agent_config_path: str | Path,
    llm_config_path: str | Path,
) -> ClarificationService:
    catalog = TemplateRepository(templates_path).load()
    agent_cfg = load_agent_config(agent_config_path)
    llm_cfg = load_llm_config(llm_config_path, {})
    model = build_langchain_chat_model(llm_cfg)
    llm = LangChainLLMEnhancer(
        model,
        strict_json_only=agent_cfg.strict_json_only,
        debug=agent_cfg.debug,
    )

    mode_service = ModeResolverService(catalog, llm=llm, enable_mode_router=agent_cfg.enable_mode_router)
    slot_service = SlotFillingService(
        catalog,
        llm=llm,
        fill_only_empty_slots=agent_cfg.fill_only_empty_slots,
    )
    question_service = QuestionPlanningService(
        catalog,
        llm=llm,
        max_questions_per_turn=agent_cfg.max_questions_per_turn,
    )
    composition_service = PromptCompositionService(
        catalog,
        llm=llm,
        capability_provider=DisabledCapabilityProvider(),
        enable_refinement=agent_cfg.enable_prompt_refinement,
    )
    validation_service = ValidationService(catalog)
    repair_service = RepairService(
        llm=llm,
        enable_repair=agent_cfg.enable_validation_repair,
    )
    session_service = SessionService(catalog, SessionExporter())
    return ClarificationService(
        catalog=catalog,
        mode_service=mode_service,
        slot_service=slot_service,
        question_service=question_service,
        composition_service=composition_service,
        validation_service=validation_service,
        repair_service=repair_service,
        session_service=session_service,
        llm=llm,
    )


def run_agent(args: argparse.Namespace) -> None:
    try:
        service = build_clarification_service(
            templates_path=args.config,
            agent_config_path=args.agent_config,
            llm_config_path=args.llm_config,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Agent 启动失败：{exc}")
        print("请先确认 langchain-openai 已安装，且 llm.yaml / 环境变量中的本地模型配置正确。")
        return
    print("Hello Prompt Agent Framework (LLM choice-first)")
    print("直接描述你的任务，我会尽量把后续交互收敛成选择题。")
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
            user = _read_paste()
            if not user:
                print("（空输入，已取消）")
                continue
        if _requires_llm_wait(user):
            print("\nAgent> 正在思考并生成候选项，请稍等...", flush=True)
        result = dispatch_agent_input(service, user)
        print("\nAgent>")
        print(result.text)
        print("-" * 72)
        if result.done:
            print("（当前共享 prompt 文档已基本成型。你可以继续 /revise、/repair 或 /reset。）")
            print("-" * 72)


def dispatch_agent_input(service: ClarificationService, user: str):
    if user == "/help":
        return service_mode_help()
    if user == "/templates":
        from hpa.application.clarification_service import InteractionResult

        return InteractionResult(text=service.mode_menu_text(), done=False)
    if user.startswith("/mode"):
        parts = user.split()
        if len(parts) != 3:
            from hpa.application.clarification_service import InteractionResult

            return InteractionResult(text="用法：/mode <CATEGORY> <SUBTYPE>，例如：/mode CODE EXTEND")
        _, cat, sub = parts
        try:
            return service.set_mode(cat, sub)
        except ValueError as exc:
            from hpa.application.clarification_service import InteractionResult

            return InteractionResult(text=str(exc))
    if user == "/show":
        return service.show_state()
    if user == "/doc":
        return service.show_document()
    if user.startswith("/clear"):
        parts = user.split(maxsplit=1)
        if len(parts) != 2:
            from hpa.application.clarification_service import InteractionResult

            return InteractionResult(text="用法：/clear <slot>")
        return service.clear_slot(parts[1])
    if user.startswith("/revise"):
        parts = user.split(maxsplit=2)
        if len(parts) < 2:
            from hpa.application.clarification_service import InteractionResult

            return InteractionResult(text="用法：/revise <section> [instruction]")
        section_key = parts[1]
        instruction = parts[2] if len(parts) == 3 else None
        return service.revise_document(section_key, instruction)
    if user == "/export":
        return service.export()
    if user == "/draft":
        return service.compose_draft()
    if user == "/lint":
        return service.lint()
    if user == "/repair":
        return service.repair()
    if user == "/reset":
        return service.reset()
    return service.handle_user_message(user)


def service_mode_help():
    from hpa.application.clarification_service import InteractionResult

    return InteractionResult(
        text=(
            "命令：\n"
            "- /templates 显示模板\n"
            "- /mode <CATEGORY> <SUBTYPE> 手动指定 mode\n"
            "- /show 查看当前 facts / 缺失项 / 等待中的选择题\n"
            "- /doc 查看共享 prompt 文档\n"
            "- /revise <section> [instruction] 对某个 section 生成改写选项\n"
            "- /clear <slot> 清空单个槽位\n"
            "- /draft 生成当前草稿\n"
            "- /lint 校验当前草稿\n"
            "- /repair 尝试修复当前草稿\n"
            "- /export 导出当前会话 JSON\n"
            "- /reset 重置\n"
            "- /paste 进入多行粘贴模式（CLI）\n"
            "\n"
            "交互方式：优先直接输入一个任务描述；当我给出选择题时，输入数字即可。"
        ),
        done=False,
    )


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


def _requires_llm_wait(user: str) -> bool:
    instant_commands = {
        "/help",
        "/templates",
        "/show",
        "/doc",
        "/export",
        "/reset",
    }
    if user in instant_commands:
        return False
    if user.startswith("/clear"):
        return False
    if user.startswith("/lint"):
        return False
    return True
