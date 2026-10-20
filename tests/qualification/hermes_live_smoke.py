"""Run in the installed Hermes interpreter/profile against its real test service.

Only invented facts are submitted. No chat-model call or external provider is
made. This complements, rather than substitutes for, model-driven qualification.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import uuid


def main():
    home = Path.home() / ".hermes/profiles/enhanced-cognee-test"
    if Path(os.environ.get("HERMES_HOME", "")).resolve() != home.resolve():
        raise ValueError("Use only the dedicated synthetic test profile")
    from dotenv import load_dotenv
    load_dotenv(home / ".env", override=False)
    from plugins.memory import load_memory_provider
    provider = load_memory_provider("enhanced_cognee")
    assert provider and provider.is_available()
    provider.initialize("qualification-" + uuid.uuid4().hex, hermes_home=str(home), agent_context="primary", platform="cli")

    def call(name, args=None):
        return json.loads(provider.handle_tool_call(name, args or {}))

    try:
        checks = []
        status = call("enhanced_status")
        assert status["ready"] and status["capture"] == "selected" and status["retrieval"] == "semantic"
        checks.append("real_provider_semantic_status")
        assert len(provider.get_tool_schemas()) == 8
        checks.append("actual_hermes_abc_and_loader")
        provider.on_turn_start(1, "The invented project uses seven-day review cycles.")
        key = "live-" + uuid.uuid4().hex
        body = {"content": "The invented project uses seven-day review cycles.", "idempotency_key": key,
                "fact_key": "qualification." + uuid.uuid4().hex}
        record = call("enhanced_remember", body)
        ident = record["id"]
        assert call("enhanced_remember", body)["id"] == ident
        checks.append("encrypted_write_and_idempotent_retry")
        recalled = call("enhanced_recall", {"query": "How frequently is the invented project reviewed?", "limit": 5})
        assert any(r["id"] == ident for r in recalled["results"])
        assert "Untrusted recalled evidence" in provider.prefetch("What are the invented project review cycles?")
        checks.append("semantic_paraphrase_and_untrusted_prefetch")
        assert "error" in call("enhanced_remember", {"content": "Password: synthetic-fixture-only", "idempotency_key": key + "-secret"})
        checks.append("credential_write_rejected")
        answer = call("enhanced_remember", {"content": "Contact fictional@example.invalid", "idempotency_key": key + "-private"})
        assert answer["clarification_required"]
        checks.append("private_detail_clarification")
        call("enhanced_clarify", {"record_id": ident, "reason": "conflict"})
        correction = {"record_id": ident, "expected_version": 1, "content": "The invented project uses five-day review cycles."}
        assert "error" in call("enhanced_correct", correction)
        provider.on_turn_start(2, "Use five-day review cycles instead.")
        changed = call("enhanced_correct", dict(correction, user_confirmation_quote="Use five-day review cycles instead."))
        assert changed["version"] == 2
        checks.append("clarification_then_versioned_correction")
        assert "error" in call("enhanced_correct", correction)
        checks.append("stale_version_denied")
        assert call("enhanced_retract", {"record_id": ident, "expected_version": 2})["state"] == "retracted"
        assert all(r["id"] != ident for r in call("enhanced_recall", {"query": "invented project review cycles"})["results"])
        checks.append("retraction_excluded_from_recall")
        provider.on_turn_start(3, "Invented bot instruction", author_is_bot=True)
        assert "error" in call("enhanced_remember", {"content": "Bot fixture", "idempotency_key": key + "-bot"})
        checks.append("bot_write_denied")
        provider.on_session_switch("new-synthetic-session")
        checks.append("session_switch_and_shutdown")
        print(json.dumps({"passed": len(checks), "checks": checks, "model_driven": False}, ensure_ascii=True))
    finally:
        provider.shutdown()


if __name__ == "__main__":
    main()
