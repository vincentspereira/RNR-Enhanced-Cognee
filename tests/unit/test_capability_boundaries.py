"""File and outbound side effects fail before I/O unless explicitly admitted."""
import json
from unittest.mock import patch

import httpx
import pytest

from src.security.capabilities import (
    read_import_text, validate_destination, check_tool_capability,
    configured_database_source, fetch_import_page,
)


def test_file_import_is_disabled_without_explicit_grant(monkeypatch):
    monkeypatch.delenv("ENHANCED_CAPABILITIES", raising=False)
    with patch("os.open") as opened:
        with pytest.raises(PermissionError):
            read_import_text("/etc/passwd")
    opened.assert_not_called()


def test_file_root_symlinks_traversal_and_byte_limit(monkeypatch, tmp_path):
    root = tmp_path / "approved"
    root.mkdir()
    outside = tmp_path / "private.txt"
    outside.write_text("private fixture")
    regular = root / "fact.txt"
    regular.write_text("approved fixture")
    (root / "alias.txt").symlink_to(outside)
    (root / "directory_alias").symlink_to(tmp_path, target_is_directory=True)
    monkeypatch.setenv("ENHANCED_CAPABILITIES", "file_import")
    monkeypatch.setenv("ENHANCED_IMPORT_ROOTS", json.dumps([str(root)]))
    assert read_import_text(str(regular)) == "approved fixture"
    for path in [outside, root / ".." / "private.txt", root / "alias.txt", root / "directory_alias" / "private.txt"]:
        with pytest.raises(OSError):
            read_import_text(str(path))
    monkeypatch.setenv("ENHANCED_MAX_IMPORT_BYTES", "4")
    with pytest.raises(ValueError):
        read_import_text(str(regular))


@pytest.mark.parametrize("url", ["http://localhost", "file:///etc/passwd", "https://other", "https://user:pass@approved", "https://approved:443", "https://approved.evil", "https://approved/#fragment"])
def test_destination_requires_exact_approved_origin(monkeypatch, url):
    monkeypatch.setenv("ENHANCED_CAPABILITIES", "notifications")
    monkeypatch.setenv("ENHANCED_OUTBOUND_ORIGINS", '["https://approved"]')
    with pytest.raises(PermissionError):
        validate_destination(url)


def test_approved_destination_and_tool_grant(monkeypatch):
    monkeypatch.setenv("ENHANCED_CAPABILITIES", "notifications")
    monkeypatch.setenv("ENHANCED_OUTBOUND_ORIGINS", '["https://approved"]')
    assert validate_destination("https://approved/hook") == "https://approved/hook"
    with pytest.raises(PermissionError):
        check_tool_capability("ingest_url")


def test_malformed_allowlist_fails_closed(monkeypatch):
    monkeypatch.setenv("ENHANCED_CAPABILITIES", "notifications")
    monkeypatch.setenv("ENHANCED_OUTBOUND_ORIGINS", '"https://approved"')
    with pytest.raises(PermissionError):
        validate_destination("https://approved")


def test_tenant_identity_cannot_enable_global_upstream_pipeline(monkeypatch):
    from src.security.enterprise_auth import principal_from_claims
    monkeypatch.setenv("ENHANCED_CAPABILITIES", "legacy_global_pipeline,web_import,database_import")
    monkeypatch.delenv("ENHANCED_REQUIRE_TENANT", raising=False)
    admin = principal_from_claims({"sub": "operator", "roles": ["admin"], "tenant": "project_owner"}, "jwt")
    with pytest.raises(PermissionError, match="tenant isolation"):
        check_tool_capability("recall", admin)


def test_database_import_uses_only_operator_source_and_query(monkeypatch):
    monkeypatch.setenv("ENHANCED_CAPABILITIES", "database_import")
    source = {"connection_string": "postgresql://readonly:synthetic@approved/fixture", "query": "SELECT * FROM approved_table"}
    monkeypatch.setenv("ENHANCED_DATABASE_SOURCES", json.dumps({"reporting": source}))
    assert configured_database_source("reporting", None) == source
    for alias, query in [(source["connection_string"], None), ("reporting", "DELETE FROM approved_table"), ("unknown", None)]:
        with pytest.raises(PermissionError):
            configured_database_source(alias, query)
    monkeypatch.setenv("ENHANCED_DATABASE_SOURCES", json.dumps({"local": dict(source, connection_string="sqlite:////etc/private.db")}))
    with pytest.raises(PermissionError):
        configured_database_source("local", None)


@pytest.mark.asyncio
@pytest.mark.parametrize("status,media,body,accepted", [
    (200, "text/plain", b"approved fixture", True),
    (302, "text/plain", b"redirect fixture", False),
    (200, "application/octet-stream", b"binary fixture", False),
    (200, "text/plain", b"x" * 129, False),
])
async def test_web_import_refuses_redirects_binary_and_oversized_responses(monkeypatch, status, media, body, accepted):
    monkeypatch.setenv("ENHANCED_CAPABILITIES", "web_import")
    monkeypatch.setenv("ENHANCED_OUTBOUND_ORIGINS", '["https://approved"]')
    monkeypatch.setenv("ENHANCED_MAX_IMPORT_BYTES", "128")
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(status, headers={"content-type": media, "location": "http://127.0.0.1/private"}, content=body)

    original = httpx.AsyncClient

    def client(**kwargs):
        assert kwargs["trust_env"] is False and kwargs["follow_redirects"] is False
        return original(**kwargs, transport=httpx.MockTransport(respond))

    monkeypatch.setattr(httpx, "AsyncClient", client)
    if accepted:
        assert await fetch_import_page("https://approved/page") == body.decode()
    else:
        with pytest.raises(ValueError):
            await fetch_import_page("https://approved/page")
    assert len(requests) == 1
    assert str(requests[0].url) == "https://approved/page"
    with pytest.raises(PermissionError):
        await fetch_import_page("https://unapproved/page")
    assert len(requests) == 1
