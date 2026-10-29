"""Local graph authority import boundaries; no credentials or store access."""
import importlib.util
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment/import_launch_graph_authority.py"
spec = importlib.util.spec_from_file_location("graph_authority_import", SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


@pytest.mark.parametrize("username,password", [("", "invented"), ("bad:name", "invented"),
    ("two words", "invented"), ("invented", ""), ("invented", "bad\nvalue"), ("invented", "bad\x00value"),
    ("ARCADEDB_PASSWORD", "invented"), ("ARCADEDB_USER", "invented"), ("ARCADEDB_USERNAME", "invented")])
def test_malformed_identity_rejected_without_echo(username, password):
    with pytest.raises(ValueError, match="^invalid_local_graph_identity$"):
        helper.authority_document(username, password)


def test_password_punctuation_preserved_and_no_extra_authority_fields():
    assert helper.authority_document("invented_admin", "invented:$'\\ space") == {
        "INDEX_ARCADEDB_USER": "invented_admin", "INDEX_ARCADEDB_PASSWORD": "invented:$'\\ space"}


def test_unprivileged_import_stops_before_prompt_or_write(monkeypatch):
    monkeypatch.setattr(helper.os, "geteuid", lambda: 1000)
    monkeypatch.setattr(helper.getpass, "getpass", lambda *a: pytest.fail("must not prompt"))
    with pytest.raises(ValueError, match="root_operator_terminal_required"):
        helper.main()
