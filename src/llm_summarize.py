"""LLM-assisted memory features (Stage D families 3 and 4, route A).

The model route lives in a root-owned LoadCredential file (llm.json) the
service reads at startup: base_url, api_key, model, daily_token_cap. The
key never enters agent space, logs, or receipts. A per-process daily
per-project token budget fails soft: exhausting it reports unavailability
and never blocks memory itself. Language detection is script-based and
needs no model.
"""
from __future__ import annotations

import datetime as _dt
import getpass
import json
import os
import re
import time
from http.client import HTTPConnection, HTTPSConnection
from pathlib import Path
from urllib.parse import urlsplit

MAX_PROMPT_CHARS = 24000
MAX_REPLY_CHARS = 16000
DEFAULT_DAILY_TOKEN_CAP = 50000


class LlmUnavailable(ValueError):
    """Fixed ASCII reasons only; never includes model content or the key."""


def load_route_env():
    """Route from the daemon's whitelisted env (preferred under systemd)."""
    base_url = os.environ.get("ENHANCED_LLM_BASE_URL")
    api_key = os.environ.get("ENHANCED_LLM_API_KEY")
    model = os.environ.get("ENHANCED_LLM_MODEL")
    if not base_url and not api_key and not model:
        return None
    if not all(isinstance(v, str) and v.strip() for v in (base_url, api_key, model)):
        raise LlmUnavailable("The model route environment is incomplete")
    parts = urlsplit(base_url)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise LlmUnavailable("The model route must be an https origin without credentials")
    try:
        cap = int(os.environ.get("ENHANCED_LLM_TOKEN_CAP", DEFAULT_DAILY_TOKEN_CAP))
    except (TypeError, ValueError):
        raise LlmUnavailable("The daily token cap is invalid")
    if not 1000 <= cap <= 10_000_000:
        raise LlmUnavailable("The daily token cap is out of range")
    return {"base_url": base_url.rstrip("/"), "api_key": api_key, "model": model,
            "daily_token_cap": cap}


def load_route(credentials_directory: str | None):
    route = load_route_env()
    if route is not None:
        return route
    if not credentials_directory:
        return None
    path = Path(credentials_directory) / "llm.json"
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text())
    except (OSError, ValueError):
        raise LlmUnavailable("The model route configuration is unreadable")
    if not isinstance(raw, dict):
        raise LlmUnavailable("The model route configuration is malformed")
    base_url = raw.get("base_url")
    api_key = raw.get("api_key")
    model = raw.get("model")
    if not all(isinstance(v, str) and v.strip() for v in (base_url, api_key, model)):
        raise LlmUnavailable("The model route configuration is incomplete")
    parts = urlsplit(base_url)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise LlmUnavailable("The model route must be an https origin without credentials")
    try:
        cap = int(raw.get("daily_token_cap", DEFAULT_DAILY_TOKEN_CAP))
    except (TypeError, ValueError):
        raise LlmUnavailable("The daily token cap is invalid")
    if not 1000 <= cap <= 10_000_000:
        raise LlmUnavailable("The daily token cap is out of range")
    return {"base_url": base_url.rstrip("/"), "api_key": api_key, "model": model,
            "daily_token_cap": cap}


class TokenBudget:
    """Per-process, per-project, per-UTC-day accounting (restart resets)."""

    def __init__(self):
        self._used: dict[tuple[str, str], int] = {}

    @staticmethod
    def _day() -> str:
        return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")

    def used(self, project: str) -> int:
        return self._used.get((self._day(), project), 0)

    def allows(self, route, project: str, estimate: int) -> bool:
        return self.used(project) + estimate <= route["daily_token_cap"]

    def charge(self, project: str, tokens: int) -> None:
        key = (self._day(), project)
        self._used[key] = self._used.get(key, 0) + max(0, int(tokens))


def chat(route, messages, *, max_tokens: int = 900, timeout: int = 45):
    """One bounded chat completion; returns (text, usage_tokens)."""
    parts = urlsplit(route["base_url"])
    connection = (HTTPSConnection(parts.hostname, parts.port or 443, timeout=timeout)
                  if parts.scheme == "https"
                  else HTTPConnection(parts.hostname, parts.port or 80, timeout=timeout))
    body = json.dumps({"model": route["model"], "messages": messages,
                       "max_tokens": max_tokens, "temperature": 0.2},
                      ensure_ascii=True).encode()
    path = (parts.path or "/").rstrip("/") + "/chat/completions"
    started = time.monotonic()
    try:
        connection.request("POST", path, body,
                           headers={"Authorization": "Bearer " + route["api_key"],
                                    "Content-Type": "application/json"})
        response = connection.getresponse()
        raw = response.read(MAX_REPLY_CHARS * 4 + 1)
        if response.status != 200:
            raise LlmUnavailable("The model route refused the request (HTTP %d)"
                                 % response.status)
        if len(raw) > MAX_REPLY_CHARS * 4:
            raise LlmUnavailable("The model reply exceeded its budget")
        payload = json.loads(raw)
        text = payload.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = payload.get("usage", {}).get("total_tokens", 0)
        if not isinstance(text, str) or not text.strip():
            raise LlmUnavailable("The model returned no usable content")
        return text[:MAX_REPLY_CHARS], int(usage or 0)
    except LlmUnavailable:
        raise
    except OSError as exc:
        raise LlmUnavailable("The model route is unreachable") from exc
    except (ValueError, KeyError, IndexError) as exc:
        raise LlmUnavailable("The model reply was malformed") from exc
    finally:
        connection.close()
        del started


_SCRIPTS = (
    ("hiragana_katakana", "ja", ((0x3040, 0x30FF),)),
    ("hangul", "ko", ((0xAC00, 0xD7AF), (0x1100, 0x11FF))),
    ("cjk", "zh", ((0x4E00, 0x9FFF),)),
    ("cyrillic", "ru", ((0x0400, 0x04FF),)),
    ("greek", "el", ((0x0370, 0x03FF),)),
    ("arabic", "ar", ((0x0600, 0x06FF),)),
    ("hebrew", "he", ((0x0590, 0x05FF),)),
    ("devanagari", "hi", ((0x0900, 0x097F),)),
    ("thai", "th", ((0x0E00, 0x0E7F),)),
)


def detect_language(text: str) -> dict:
    """Unicode-script heuristic; ASCII-dominant text reports English."""
    if not isinstance(text, str) or not text.strip():
        raise LlmUnavailable("No text supplied")
    counts = {}
    for character in text[:4000]:
        code = ord(character)
        if code < 128:
            counts["latin"] = counts.get("latin", 0) + 1
            continue
        for name, _, ranges in _SCRIPTS:
            if any(low <= code <= high for low, high in ranges):
                counts[name] = counts.get(name, 0) + 1
                break
        else:
            counts["other"] = counts.get("other", 0) + 1
    non_latin = {name: count for name, count in counts.items()
                 if name not in ("latin", "other")}
    if not non_latin:
        language, script, matched = "en", "latin", counts.get("latin", 0)
    else:
        name = max(non_latin, key=non_latin.get)
        script, language = name, dict(
            (entry[0], entry[1]) for entry in _SCRIPTS)[name]
        matched = non_latin[name]
    total = sum(counts.values()) or 1
    return {"language": language, "script": script,
            "confidence": round(matched / total, 2), "method": "script_heuristic"}


def summarize_messages(records, title: str | None) -> list[dict]:
    """Bounded prompt over record contents."""
    lines = []
    used = 0
    for record in records:
        ident = str(record.get("id", ""))[:40]
        content = str(record.get("content", ""))[:600]
        line = "- [%s] %s" % (ident, content.replace("\n", " "))
        if used + len(line) > MAX_PROMPT_CHARS:
            break
        lines.append(line)
        used += len(line)
    if not lines:
        raise LlmUnavailable("Nothing to summarize")
    topic = title or "this profile's recent memories"
    return [
        {"role": "system", "content": "You summarize memory records. Reply with "
         "a compact factual digest under 300 words. ASCII output only. Never "
         "invent facts; omit anything uncertain."},
        {"role": "user", "content": "Summarize %s:\n\n%s" % (topic, "\n".join(lines))},
    ]


def consolidation_messages(records) -> list[dict]:
    """Ask the model which records look like duplicates/merge candidates."""
    lines = []
    used = 0
    for record in records:
        ident = str(record.get("id", ""))[:40]
        content = str(record.get("content", ""))[:200]
        line = "- [%s] %s" % (ident, content.replace("\n", " "))
        if used + len(line) > MAX_PROMPT_CHARS:
            break
        lines.append(line)
        used += len(line)
    if len(lines) < 2:
        raise LlmUnavailable("Too few records to compare")
    return [
        {"role": "system", "content": "You find duplicate or mergeable memory "
         "records. Reply with ONLY a JSON object: {\"groups\": [[\"id\",\"id\"],...]} "
         "listing record ids that state the same fact. No explanations."},
        {"role": "user", "content": "Records:\n\n%s" % "\n".join(lines)},
    ]


def parse_consolidation(reply: str) -> dict:
    match = re.search(r"\{.*\}", reply, re.DOTALL)
    if not match:
        return {"groups": []}
    try:
        payload = json.loads(match.group(0))
    except ValueError:
        return {"groups": []}
    groups = payload.get("groups")
    if not isinstance(groups, list):
        return {"groups": []}
    clean = []
    for group in groups:
        if (isinstance(group, list) and len(group) >= 2
                and all(isinstance(item, str) and 0 < len(item) <= 40
                        for item in group)):
            clean.append(group[:8])
    return {"groups": clean[:32]}


def translate_messages(text: str, target_language: str) -> list[dict]:
    if not isinstance(text, str) or not 1 <= len(text) <= 8000:
        raise LlmUnavailable("Text length out of range for translation")
    if not isinstance(target_language, str) or not 2 <= len(target_language.strip()) <= 32:
        raise LlmUnavailable("Invalid target language")
    return [
        {"role": "system", "content": "You translate faithfully. Output only "
         "the translation, no commentary."},
        {"role": "user", "content": "Translate to %s:\n\n%s" %
         (target_language.strip(), text)},
    ]
