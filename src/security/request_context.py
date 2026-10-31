"""Trusted identity for HTTP and stdio calls; never inferred from tool arguments."""
from __future__ import annotations

from contextlib import contextmanager
from contextlib import nullcontext
from contextvars import ContextVar
from typing import Any, Iterator, Optional

from src.security.enterprise_auth import AuthError, Principal
from src.security.auth import Role

_CALLER: ContextVar[Optional[Principal]] = ContextVar("enhanced_cognee_caller", default=None)


def current_principal() -> Optional[Principal]:
    return _CALLER.get()


@contextmanager
def principal_context(principal: Principal) -> Iterator[Principal]:
    token = _CALLER.set(principal)
    try:
        yield principal
    finally:
        _CALLER.reset(token)


@contextmanager
def storage_call_context(principal: Principal):
    from src.multi_tenant import TenantContext, get_tenant
    tenant = principal.tenant_id or get_tenant()
    if principal.role != Role.ADMIN and not tenant:
        raise AuthError(403, "Restricted storage callers require an assigned tenant.")
    with principal_context(principal), TenantContext(tenant) if tenant else nullcontext():
        yield


def validate_identity_fields(arguments: dict[str, Any], principal: Principal) -> None:
    """Prevent a restricted caller from impersonating another writer or tenant."""
    if not isinstance(arguments, dict):
        raise AuthError(422, "Tool arguments must be a JSON object.")
    if principal.role == Role.ADMIN:
        return
    expected_agent = str(principal.claims.get("agent_id") or principal.subject)
    for field, expected in (("agent_id", expected_agent), ("user_id", principal.subject),
                            ("tenant_id", principal.tenant_id),
                            ("project_id", principal.claims.get("project_id"))):
        value = arguments.get(field)
        if value is not None and str(value) != str(expected):
            raise AuthError(403, f"Caller cannot select another {field}.")
    # Never let a nested filter override an authoritative scope.
    filters = arguments.get("filters")
    if isinstance(filters, dict):
        validate_identity_fields(filters, principal)
