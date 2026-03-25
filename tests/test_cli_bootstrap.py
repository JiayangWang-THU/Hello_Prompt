from __future__ import annotations

from hpa.cli import build_parser
from hpa.interfaces.cli_agent import dispatch_agent_input

from .test_helpers import FakeLLMEnhancer, build_service, make_mode_choice


def test_show_no_longer_depends_on_old_assisted_engine():
    service = build_service(llm=FakeLLMEnhancer(mode_choice=make_mode_choice("CODE/EXTEND")))
    service.handle_user_message("我要改一个 CLI")
    result = service.show_state()
    assert "当前等待中的收敛建议" in result.text


def test_cli_dispatch_handles_doc_command():
    service = build_service(llm=FakeLLMEnhancer(mode_choice=make_mode_choice("CODE/EXTEND")))
    service.handle_user_message("我要改一个 CLI")
    dispatched = dispatch_agent_input(service, "/doc")
    assert "当前还没有共享 prompt 文档" in dispatched.text


def test_cli_parser_includes_web_command():
    parser = build_parser()
    args = parser.parse_args(["web"])
    assert args.command == "web"
    assert args.host == "127.0.0.1"
    assert args.port == 7860


def test_snapshot_exposes_document_sections_for_web_ui():
    service = build_service(llm=FakeLLMEnhancer(mode_choice=make_mode_choice("CODE/EXTEND")))
    service.handle_user_message("我要改一个 CLI")
    service.handle_user_message("1")
    service.compose_draft()
    snapshot = service.snapshot()
    assert snapshot["mode_key"] == "CODE/EXTEND"
    assert snapshot["document"] is not None
    assert snapshot["document"]["sections"]
