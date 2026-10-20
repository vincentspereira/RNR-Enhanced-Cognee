"""Safe operator updates preserve the synthetic profile and recovery originals."""
import importlib.util
import json
from pathlib import Path

import jwt
import pytest


def operator(monkeypatch, tmp_path):
    path = Path("integrations/hermes/deployment/test_service.py").resolve()
    spec = importlib.util.spec_from_file_location("hermes_operator_fixture", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    profile = tmp_path / ".hermes/profiles/enhanced-cognee-test"
    plugin = profile / "plugins/enhanced_cognee"
    plugin.mkdir(parents=True)
    (profile / "enhanced-cognee-qualification.json").write_text('{"synthetic_only":true}')
    root = tmp_path / "agent-workspace/enhanced-cognee-test-runtime"
    (root / "secrets").mkdir(parents=True)
    return module, root, profile, plugin


def test_upgrade_archives_originals_and_keeps_extra_files(monkeypatch, tmp_path):
    module, root, profile, plugin = operator(monkeypatch, tmp_path)
    (plugin / "__init__.py").write_text("# Original synthetic provider\n")
    (plugin / "owner-notes.txt").write_text("Synthetic retained owner notes")
    module.upgrade_plugin(root)
    archived = list(profile.glob("provider-before-upgrade-*"))
    assert len(archived) == 1 and (archived[0] / "__init__.py").read_text() == "# Original synthetic provider\n"
    assert archived[0].stat().st_mode & 0o077 == 0
    assert (plugin / "owner-notes.txt").read_text() == "Synthetic retained owner notes"
    assert (plugin / "__init__.py").read_bytes() == (module.REPO / "integrations/hermes/enhanced_cognee/__init__.py").read_bytes()
    (plugin / "client.py").rename(plugin / "original-client.py")
    (plugin / "client.py").symlink_to(plugin / "original-client.py")
    with pytest.raises(ValueError, match="symlink"):
        module.upgrade_plugin(root)


def test_token_renewal_keeps_other_settings_and_never_copies_signing_key(monkeypatch, tmp_path):
    module, root, profile, plugin = operator(monkeypatch, tmp_path)
    secret = "synthetic-operator-signing-key-at-least-32-bytes"
    config = root / "secrets/service.json"
    config.write_text(json.dumps({"ENHANCED_JWT_SECRET": secret}))
    config.chmod(0o600)
    env = profile / ".env"
    original = "OTHER_SETTING=retained\nENHANCED_COGNEE_ACCESS_TOKEN=synthetic-expired-token\n"
    env.write_text(original)
    module.renew_test_token(root)
    current = env.read_text()
    assert current.startswith("OTHER_SETTING=retained\n") and secret not in current
    assert env.stat().st_mode & 0o077 == 0
    assert list(profile.glob("env-before-token-renewal-*"))[0].read_text() == original
    token = current.split("ENHANCED_COGNEE_ACCESS_TOKEN=", 1)[1].strip()
    claims = jwt.decode(token, secret, algorithms=["HS256"])
    assert claims["project_id"] == "hermes_test" and claims["tenant"] == "qualification"
    assert claims["roles"] == ["api_client"] and claims["capture_policy"] == "selected"
