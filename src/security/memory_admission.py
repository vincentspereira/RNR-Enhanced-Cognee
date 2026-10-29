"""Always-on credential exclusion for canonical memory, independent of models."""
from __future__ import annotations

import json
import re


_CREDENTIALS = (
    re.compile(r"AGE-SECRET-KEY-1[A-Z0-9]{20,}"),
    re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----", re.I),
    re.compile(r"\b(?:sk-(?:proj-|ant-)?|github_pat_|ghp_|gho_|xox[baprs]-)[A-Za-z0-9_-]{16,}"),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\b(?:password|passwd|api[_ -]?key|access[_ -]?(?:key|token)|private[_ -]?key|master[_ -]?key|signing[_ -]?key|secret)"
               r"\b[\"']?\s*(?:=|:|is)\s*[\"']?[^\s\"',;]{1,}", re.I),
    re.compile(r"\b(?:Bearer|Basic)\s+[A-Za-z0-9+/=_\-.]{8,}", re.I),
    re.compile(r"[a-z][a-z0-9+.-]*://[^\s/:]+:[^\s/@]+@", re.I),
    re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{43}=(?![=A-Za-z0-9_-])"),
    re.compile(r"https://hooks\.slack\.com/services/[^\s\"']+", re.I),
)
_PERSONAL = (
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b(?:\d[ -]?){13,19}\b"),
    re.compile(r"\b(?:passport|national insurance|social security|home address|medical diagnosis)\b", re.I),
    re.compile(r"(?:\+\d{1,3}[ -]?)?(?:\(?\d{3,5}\)?[ -])\d{3,4}[ -]\d{3,4}\b"),
)


def contains_credentials(text: str) -> bool:
    return any(pattern.search(text) for pattern in _CREDENTIALS)


def require_no_credentials(text: str) -> None:
    if contains_credentials(text):
        raise ValueError("Credential-shaped content cannot be admitted as memory")


def contains_private_details(text: str) -> bool:
    """Conservative publication/capture screen, not a complete privacy classifier."""
    return contains_credentials(text) or any(pattern.search(text) for pattern in _PERSONAL)


def contains_private_memory_details(record: dict) -> bool:
    """Screen memory data, excluding service-generated retrieval bookkeeping.

    Internal UUIDs can resemble phone numbers and embedding decimals can resemble
    payment-card numbers. Neither is caller-provided memory text. Nested metadata,
    provenance, evidence, categories and links remain screened without exclusions.
    Use this only for canonical read results; admission still screens every
    caller-controlled field before storage.
    """
    internal = {"id", "version", "project_id", "state", "created_at", "updated_at",
                "expires_at", "shared", "embedding", "embedding_model"}
    visible = {key: value for key, value in record.items() if key not in internal}
    return contains_private_details(json.dumps(visible, ensure_ascii=True))
