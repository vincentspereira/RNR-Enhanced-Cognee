"""Profile-owner transaction for an operator-authorized ordinary credential.

Reuses the reviewed issuer file guards and renewal journal/reconciliation code.
No signing key, account selection or signing choices enter this child function.
The operator driver must validate the root-owned allowlist and bound its receipt.
Publication does not qualify a running Hermes process or enable a timer.
"""
from __future__ import annotations

import json
import os
import time
import uuid


def accepted_status(core, token):
    code, data = core["api_status"](token)
    expected = {"tenant_id": core["IDENTITY"]["tenant"], "project_id": core["IDENTITY"]["project_id"],
                "subject": core["IDENTITY"]["sub"]}
    if (code != 200 or not isinstance(data, dict) or data.get("ready") is not True
            or data.get("schema_version") != 3 or data.get("encryption") != "AES-256-GCM"
            or any(data.get(key) != value for key, value in expected.items())
            or type(data.get("active_records")) is not int or data["active_records"] < 0
            or type(data.get("pending_change_events")) is not int or data["pending_change_events"] < 0):
        raise ValueError("renewal_scope_or_api_refused")


def publish(core, renewal, directory, bundle, uid, *, checkpoint=lambda phase: None):
    """One bounded attempt. Caller holds the exclusive per-profile renewal lock."""
    if not isinstance(bundle, dict) or set(bundle) != {"token", "expired", "altered", "claims"}:
        raise ValueError("renewal_bundle_shape")
    claims = renewal["token_claims"](core, bundle["token"])
    if claims != bundle["claims"] or not 0 <= int(time.time()) - claims["iat"] <= 120:
        raise ValueError("renewal_bundle_stale_or_wrong_scope")
    original, _ = core["read_private_at"](directory, ".env", uid)
    previous = renewal["environment"](core, original)
    if previous == bundle["token"]:
        raise ValueError("credential_already_current")
    recovered = renewal["reconcile"](core, directory, uid, original)
    preserved = {name: core["read_private_at"](directory, name, uid)[0]
                 for name in ("config.yaml", "enhanced_cognee.json", "auth.json")}
    settings = json.loads(preserved["enhanced_cognee.json"])
    if (not isinstance(settings, dict) or settings.get("base_url") != "http://127.0.0.1:28080"
            or settings.get("capture_policy") != "selected"
            or type(settings.get("include_shared")) is not bool):
        raise ValueError("renewal_profile_binding_differs")
    # Existing, unexpired credentials must still authenticate. Expired-profile
    # recovery is an explicit operator task; unattended renewal fails closed.
    old_claims = renewal["token_claims"](core, previous)
    if old_claims["exp"] <= int(time.time()):
        raise ValueError("expired_profile_requires_operator_recovery")
    accepted_status(core, previous)
    for token in (None, bundle["expired"], bundle["altered"]):
        if core["api_status"](token)[0] != 401:
            raise ValueError("renewal_refusal_control_failed")
    accepted_status(core, bundle["token"])
    updated = renewal["environment"](core, original, bundle["token"])
    ident = uuid.uuid4().hex
    backup, candidate = ".env-before-cognee-renew-" + ident, ".env-cognee-renew-" + ident
    name = ".cognee-renewal-" + ident + ".json"
    journal = {"backup": backup, "candidate": candidate,
               "before": renewal["digest"](original), "after": renewal["digest"](updated)}
    core["create_private_at"](directory, backup, original)
    core["create_private_at"](directory, candidate, updated)
    if (core["read_private_at"](directory, backup, uid)[0] != original
            or core["read_private_at"](directory, candidate, uid)[0] != updated):
        raise ValueError("renewal_staged_copies_differ")
    core["create_private_at"](directory, name, json.dumps(journal).encode())
    os.fsync(directory)
    checkpoint("prepared")
    if (core["read_private_at"](directory, ".env", uid)[0] != original
            or any(core["read_private_at"](directory, key, uid)[0] != raw for key, raw in preserved.items())):
        raise ValueError("renewal_profile_changed")
    os.replace(candidate, ".env", src_dir_fd=directory, dst_dir_fd=directory)
    os.fsync(directory)
    checkpoint("published")
    if (core["read_private_at"](directory, ".env", uid)[0] != updated
            or any(core["read_private_at"](directory, key, uid)[0] != raw for key, raw in preserved.items())):
        raise ValueError("renewal_publication_differs")
    accepted_status(core, renewal["environment"](core, updated))
    checkpoint("verified")
    renewal["finish"](core, directory, name, journal, "published")
    return {"complete": True, "credential_published": True, "preserved_settings_and_oauth": True,
            "preserved_previous_environment": True, "interrupted_attempts_reconciled": recovered,
            "native_reload_qualified": False, "timer_activation_approved": False}
