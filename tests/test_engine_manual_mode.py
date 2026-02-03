from hpa.engine import AgentEngine


def test_manual_mode_flow():
    eng = AgentEngine(cfg_path="configs/templates.json")

    # Not selected mode
    r = eng.step("hi")
    assert "/mode" in r.text

    # Select mode
    r = eng.step("/mode CODE EXTEND")
    assert "模式已设定" in r.text

    # Fill slots quickly
    eng.step("goal: do something")
    eng.step("base_system: python pkg")
    eng.step("new_features: P0 x")
    eng.step("compatibility: keep old config")
    eng.step("runtime_env: ubuntu")
    r = eng.step("output_format: Markdown")

    assert r.done is True
    assert "最终 prompt" in r.text
