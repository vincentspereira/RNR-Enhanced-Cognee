"""Operator-controlled admission of file imports and external side effects."""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from urllib.parse import urlsplit

TOOL_CAPABILITIES = {
    "load_document_with_plugin": "file_import",
    "ingest_url": "web_import",
    "ingest_db": "database_import",
    "register_webhook": "notifications", "test_webhook": "notifications",
    "configure_slack_notifications": "notifications", "configure_discord_notifications": "notifications",
    "test_notification_channel": "notifications",
}

# These upstream APIs use their own global stores. A dataset label does not
# establish isolation. Keep them outside tenant/project service profiles until
# they delegate to the canonical scoped service.
GLOBAL_UPSTREAM_TOOLS = frozenset({
    "remember", "recall", "forget_memory", "improve", "save_interaction",
    "ingest_url", "ingest_db", "cognify_status",
})


def require_capability(name: str) -> None:
    enabled = {item.strip() for item in os.getenv("ENHANCED_CAPABILITIES", "").split(",") if item.strip()}
    if name not in enabled:
        raise PermissionError(f"Capability '{name}' is disabled; an operator must explicitly enable it")


def check_tool_capability(tool: str, principal=None) -> None:
    if tool in GLOBAL_UPSTREAM_TOOLS:
        from src.multi_tenant import get_tenant, tenant_required
        from src.security.request_context import current_principal
        from src.security.auth import Role
        principal = principal or current_principal()
        if get_tenant() or tenant_required() or (principal and (principal.tenant_id or principal.role != Role.ADMIN)):
            raise PermissionError("This legacy upstream pipeline has no qualified tenant isolation")
        require_capability("legacy_global_pipeline")
    capability = TOOL_CAPABILITIES.get(tool)
    if capability:
        require_capability(capability)


def _configured_list(name: str) -> list[str]:
    try:
        values = json.loads(os.getenv(name, "[]"))
        if not isinstance(values, list) or not all(isinstance(v, str) and v for v in values):
            raise ValueError
        return values
    except (TypeError, ValueError) as exc:
        raise PermissionError("Invalid capability allowlist configuration") from exc


def read_import_text(source: str, encoding="utf-8") -> str:
    """Bounded file read beneath an explicit trusted root, with no symlink traversal.

    Open each component relative to a directory descriptor so a path replacement
    cannot turn the validation into an arbitrary file read.
    """
    require_capability("file_import")
    source_path = Path(source)
    if not source_path.is_absolute() or ".." in source_path.parts:
        raise PermissionError("File imports require an absolute path within an approved root")
    roots = [Path(root).resolve(strict=True) for root in _configured_list("ENHANCED_IMPORT_ROOTS")]
    root = next((r for r in roots if source_path.is_relative_to(r)), None)
    if root is None:
        raise PermissionError("File is outside the approved import roots")
    components = source_path.relative_to(root).parts
    if not components:
        raise PermissionError("File import requires a regular file")
    cap = int(os.getenv("ENHANCED_MAX_IMPORT_BYTES", "1048576"))
    if cap <= 0:
        raise ValueError("Invalid file import byte limit")
    flags = os.O_RDONLY | os.O_NOFOLLOW
    fd = os.open(root, flags | os.O_DIRECTORY)
    try:
        for part in components[:-1]:
            child = os.open(part, flags | os.O_DIRECTORY, dir_fd=fd)
            os.close(fd)
            fd = child
        file_fd = os.open(components[-1], flags | os.O_NONBLOCK, dir_fd=fd)
        with os.fdopen(file_fd, "rb") as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                raise PermissionError("File imports require a regular file")
            data = handle.read(cap + 1)
            if len(data) > cap:
                raise ValueError("File import exceeds the configured byte limit")
        return data.decode(encoding)
    finally:
        os.close(fd)


def validate_destination(url: str, capability="notifications") -> str:
    """Require an explicit HTTPS origin grant; redirects must remain disabled."""
    require_capability(capability)
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise PermissionError("An approved HTTPS destination is required")
    origin = f"https://{parsed.netloc.lower()}"
    # This is an operator trust grant to an exact origin, not a public-host
    # heuristic. Credentials cannot supply this environment configuration.
    if origin not in _configured_list("ENHANCED_OUTBOUND_ORIGINS"):
        raise PermissionError("Destination origin has not been approved by an operator")
    return url


async def fetch_import_page(url: str) -> str:
    """Fetch only an explicitly approved page; no redirects or ambient proxy.

    The origin allowlist is an operator trust grant, including its DNS/hosting.
    No browser, JavaScript, linked resources, paid extractor, or crawler runs.
    """
    import asyncio
    import httpx
    validate_destination(url, "web_import")
    cap = int(os.getenv("ENHANCED_MAX_IMPORT_BYTES", "1048576"))
    if not 1 <= cap <= 4 * 1024 * 1024:
        raise ValueError("Web imports require a byte limit of 1-4194304")
    async with asyncio.timeout(15):
        async with httpx.AsyncClient(timeout=10, follow_redirects=False, trust_env=False) as client:
            async with client.stream("GET", url) as response:
                if response.status_code != 200:
                    raise ValueError("Approved page did not return HTTP 200; redirects are refused")
                media = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                if media not in {"text/html", "text/plain", "application/xhtml+xml"}:
                    raise ValueError("Web imports require an HTML or plain text response")
                parts, size = [], 0
                async for chunk in response.aiter_bytes(chunk_size=16384):
                    size += len(chunk)
                    if size > cap:
                        raise ValueError("Web import exceeds the configured byte limit")
                    parts.append(chunk)
                return b"".join(parts).decode(response.encoding or "utf-8", errors="replace")


def configured_database_source(alias: str, query: str | None) -> dict:
    """Resolve an operator-configured read-only source, never a caller URI/SQL.

    The configured account must be read-only at the database itself. SQLite
    and arbitrary SQLAlchemy driver strings are excluded from this public tool.
    """
    require_capability("database_import")
    if query is not None:
        raise PermissionError("Database import queries must be configured by the operator")
    try:
        sources = json.loads(os.getenv("ENHANCED_DATABASE_SOURCES", "{}"))
        source = sources[alias]
        if not isinstance(source, dict) or set(source) != {"connection_string", "query"}:
            raise ValueError
        uri = urlsplit(source["connection_string"])
        if uri.scheme not in {"postgresql", "mysql"} or not uri.hostname or not uri.path.strip("/"):
            raise ValueError
        if not isinstance(source["query"], str) or not source["query"].strip():
            raise ValueError
        return source.copy()
    except (KeyError, TypeError, ValueError):
        raise PermissionError("Select an operator-approved database source alias") from None
