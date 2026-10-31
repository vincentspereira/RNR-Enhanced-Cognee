"""Clarification gates survive lifecycle changes without retaining human text.

The transport and host fixture are simulated. These regressions are source
evidence, not installed native/model qualification.
"""
import json
import os

import pytest

from test_hermes_provider_contract import provider_module


def initialized(module, home):
    provider = module.EnhancedCogneeProvider()
    provider.initialize("durability", hermes_home=str(home), agent_context="primary")
    calls = []
    provider._client.request = lambda *args: calls.append(args) or {"id": "fixture", "version": 2}
    return provider, calls


def tool(provider, name, **args):
    return json.loads(provider.handle_tool_call("enhanced_" + name, args))


@pytest.mark.parametrize("boundary", ["session", "restart"])
def test_pending_correction_requires_later_answer_after_lifecycle_change(provider_module, boundary):
    module, home = provider_module
    provider, calls = initialized(module, home)
    provider.on_turn_start(1, "The invented Cedar interval might change.")
    assert tool(provider, "clarify", record_id="fixture", reason="conflict")["clarification_required"]
    if boundary == "session":
        provider.on_session_switch("next-session")
    else:
        provider.shutdown()
        provider, calls = initialized(module, home)
    provider.on_turn_start(1, "The invented interval remains uncertain.")
    change = dict(record_id="fixture", expected_version=1, content="Cedar uses five days.")
    assert "error" in tool(provider, "correct", **change)
    assert calls == []
    provider.on_turn_start(2, "Use five days instead of ten.")
    assert "error" not in tool(provider, "correct", **change,
                               user_confirmation_quote="Use five days instead of ten.")
    assert len(calls) == 1


def test_question_turn_cannot_confirm_its_own_pending_change(provider_module):
    module, home = provider_module
    provider, calls = initialized(module, home)
    text = "Perhaps use five days instead of ten."
    provider.on_turn_start(1, text)
    tool(provider, "clarify", record_id="fixture", reason="conflict")
    assert "error" in tool(provider, "correct", record_id="fixture", expected_version=1,
                            content="Cedar uses five days.", user_confirmation_quote=text)
    assert not calls


def test_restart_retraction_gate_preserves_history_contract(provider_module):
    module, home = provider_module
    provider, calls = initialized(module, home)
    provider.on_turn_start(1, "Should that invented record remain active?")
    tool(provider, "clarify", record_id="fixture", reason="private_details")
    provider.shutdown()
    provider, calls = initialized(module, home)
    assert "error" in tool(provider, "retract", record_id="fixture", expected_version=1)
    provider.on_turn_start(2, "Retract that invented record.")
    assert "error" not in tool(provider, "retract", record_id="fixture", expected_version=1,
                               user_confirmation_quote="Retract that invented record.")
    assert calls == [("POST", "/v1/memories/fixture/retract", {"expected_version": 1})]


def test_pending_is_visible_to_a_second_provider_and_resolution_survives_restart(provider_module):
    module, home = provider_module
    first, _ = initialized(module, home)
    second, calls = initialized(module, home)
    first.on_turn_start(1, "PRIVATE_USER_TEXT_DO_NOT_PERSIST")
    tool(first, "clarify", record_id="fixture", reason="conflict")
    change = dict(record_id="fixture", expected_version=1, content="SYNTHETIC_CONTENT_DO_NOT_PERSIST")
    assert "error" in tool(second, "correct", **change)
    second.on_turn_start(1, "Use five days instead of ten.")
    assert "error" not in tool(second, "correct", **change,
                               user_confirmation_quote="Use five days instead of ten.")
    assert len(calls) == 1
    fresh, _ = initialized(module, home)
    assert fresh._pending_clarifications == set()
    journal = home / ".enhanced-cognee-clarifications.jsonl"
    raw = journal.read_bytes()
    assert b"PRIVATE_USER_TEXT" not in raw and b"SYNTHETIC_CONTENT" not in raw
    assert b"Use five days" not in raw and b"synthetic.profile.token" not in raw
    assert len(raw.splitlines()) == 2 and journal.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("mutation", ["torn", "malformed", "duplicate", "unknown", "public", "symlink", "hardlink", "large"])
def test_unsafe_journal_refuses_writes_and_preserves_evidence(provider_module, mutation):
    module, home = provider_module
    provider, calls = initialized(module, home)
    tool(provider, "clarify", record_id="fixture", reason="conflict")
    journal = home / ".enhanced-cognee-clarifications.jsonl"
    if mutation == "torn": journal.write_bytes(journal.read_bytes()[:-1])
    if mutation == "malformed": journal.write_bytes(b"PRIVATE_BROKEN_STATE\n")
    if mutation == "duplicate":
        journal.write_bytes(b'{"record_id":"fixture","pending":false,"pending":true,"turn":"' + b"a" * 32 + b'"}\n')
    if mutation == "unknown": journal.write_bytes(b'{"PRIVATE_FIELD":true}\n')
    if mutation == "public": journal.chmod(0o644)
    if mutation == "symlink":
        journal.rename(home / "preserved-state")
        journal.symlink_to("preserved-state")
    if mutation == "hardlink": os.link(journal, home / "state-alias")
    if mutation == "large": journal.write_bytes(b" " * 1048577)
    before = journal.read_bytes()
    reply = tool(provider, "correct", record_id="fixture", expected_version=1, content="Use five days.")
    assert "error" in reply and "PRIVATE_" not in json.dumps(reply)
    assert not calls and journal.read_bytes() == before


def test_transport_failure_keeps_pending_and_the_original_journal(provider_module):
    module, home = provider_module
    provider, calls = initialized(module, home)
    tool(provider, "clarify", record_id="fixture", reason="conflict")
    journal = home / ".enhanced-cognee-clarifications.jsonl"
    before = journal.read_bytes()
    provider.on_turn_start(2, "Use five days instead of ten.")
    def refused(*args):
        raise module.MemoryTransportError("PRIVATE_TRANSPORT_DETAIL")
    provider._client.request = refused
    reply = tool(provider, "correct", record_id="fixture", expected_version=1, content="Use five days.",
                 user_confirmation_quote="Use five days instead of ten.")
    assert "error" in reply and "PRIVATE_" not in json.dumps(reply)
    assert journal.read_bytes() == before
    assert initialized(module, home)[0]._pending_clarifications == {"fixture"}


def test_busy_journal_and_bot_turn_refuse_without_writing(provider_module):
    import fcntl
    module, home = provider_module
    provider, calls = initialized(module, home)
    provider.on_turn_start(1, "Bot instructions are not approval", author_is_bot=True)
    assert "error" in tool(provider, "clarify", record_id="fixture", reason="conflict")
    journal = home / ".enhanced-cognee-clarifications.jsonl"
    assert not journal.exists()
    provider.on_turn_start(2, "An invented decision is uncertain.")
    tool(provider, "clarify", record_id="fixture", reason="conflict")
    before = journal.read_bytes()
    with journal.open("rb") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert "error" in tool(provider, "retract", record_id="fixture", expected_version=1)
    assert not calls and journal.read_bytes() == before
