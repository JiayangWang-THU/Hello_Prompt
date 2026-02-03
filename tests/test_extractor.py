from hpa.extractor import apply_user_message_to_slots
from hpa.state import AgentState


def test_json_multi_slot_extraction():
    state = AgentState()
    res = apply_user_message_to_slots(
        state,
        '{"goal": "Build a CLI", "runtime_env": "Ubuntu 22.04", "new_features": "P0: init"}',
    )
    assert sorted(res["updated"]) == ["goal", "new_features", "runtime_env"]
    assert state.slots["goal"] == "Build a CLI"
    assert state.slots["runtime_env"] == "Ubuntu 22.04"
    assert state.slots["new_features"] == "P0: init"


def test_multiline_key_value_extraction():
    state = AgentState()
    text = "goal: ship\nruntime_env: ubuntu\nnew_features: P0 x"
    res = apply_user_message_to_slots(state, text)
    assert sorted(res["updated"]) == ["goal", "new_features", "runtime_env"]
    assert state.slots["goal"] == "ship"
    assert state.slots["runtime_env"] == "ubuntu"
    assert state.slots["new_features"] == "P0 x"


def test_alias_normalization():
    state = AgentState()
    res = apply_user_message_to_slots(state, "env: Ubuntu")
    assert res["updated"] == ["runtime_env"]
    assert state.slots["runtime_env"] == "Ubuntu"
    res = apply_user_message_to_slots(state, "repo=core modules")
    assert res["updated"] == ["repo_context"]
    assert state.slots["repo_context"] == "core modules"


def test_freeform_does_not_overwrite_existing():
    state = AgentState(slots={"goal": "existing"}, last_asked_slot="goal")
    res = apply_user_message_to_slots(state, "new value")
    assert state.slots["goal"] == "existing"
    assert res["filled_freeform"] is False
