"""Fail-closed secret/config resolution for Enhanced Cognee."""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class InsecureConfigError(RuntimeError):
    """Raised when a required secret is missing and insecure defaults are not allowed."""


def _truthy(val: Optional[str]) -> bool:
    return (val or "").strip().lower() in ("1", "true", "yes", "on")


def _insecure_defaults_allowed() -> bool:
    # Never allow built-in dev defaults in production, regardless of the flag.
    if (os.getenv("ENHANCED_ENV", "").strip().lower() in ("production", "prod")):
        return False
    return _truthy(os.getenv("ENHANCED_ALLOW_INSECURE_DEFAULTS"))


def require_secret(name: str, dev_default: Optional[str] = None) -> str:
    """Return secret from env. Fail closed if missing.

    If the var is set, return it. Otherwise, only fall back to dev_default
    when ENHANCED_ALLOW_INSECURE_DEFAULTS is truthy AND ENHANCED_ENV is not
    production. Otherwise raise InsecureConfigError.
    """
    val = os.getenv(name)
    if val:
        return val
    if dev_default is not None and _insecure_defaults_allowed():
        logger.warning(
            "INSECURE: using built-in dev default for %s. "
            "Set %s via environment/.env. This is refused when ENHANCED_ENV=production.",
            name, name,
        )
        return dev_default
    raise InsecureConfigError(
        "Required secret '" + name + "' is not set. Provide it via environment or .env. "
        "Refusing to use a hardcoded default. For local dev only, set "
        "ENHANCED_ALLOW_INSECURE_DEFAULTS=1 (never in production)."
    )
