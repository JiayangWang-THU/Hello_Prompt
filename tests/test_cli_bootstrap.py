from __future__ import annotations

from hpa.interfaces.cli_agent import _dispatch_agent_input

from .test_helpers import FakeLLMEnhancer, build_service, make_mode_choice


def test_show_no_longer_depends_on_old_assisted_engine():
    service = build_service(llm=FakeLLMEnhancer(mode_choice=make_mode_choice("CODE/EXTEND")))
    service.handle_user_message("我要改一个 CLI")
    result = service.show_state()
    assert "当前等待中的选择题" in result.text


def test_cli_dispatch_handles_doc_command():
    service = build_service(llm=FakeLLMEnhancer(mode_choice=make_mode_choice("CODE/EXTEND")))
    service.handle_user_message("我要改一个 CLI")
    dispatched = _dispatch_agent_input(service, "/doc")
    assert "当前还没有共享 prompt 文档" in dispatched.text
