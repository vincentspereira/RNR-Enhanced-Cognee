"""Reviewed ingestion for the canonical memory service (Stage D, family 1).

Pure, dependency-free helpers: bounded paragraph-aware chunking, a public-
address guard for URL fetches (loopback/private/link-local/reserved are
refused on EVERY resolved address), a redirect-free bounded text fetch, a
standard-library HTML-to-text strip, and record builders that flow through
the existing remember() admission (idempotency keys, provenance metadata,
credential-pattern rejection unchanged). No LLM is involved: chunks are
stored as written, provenance-labeled.
"""
from __future__ import annotations

import ipaddress
import re
import socket
from html.parser import HTMLParser
from http.client import HTTPConnection, HTTPSConnection
from urllib.parse import urlsplit

MAX_CHUNKS = 32
MAX_CHUNK_CHARS = 2000
MAX_FETCH_BYTES = 1 << 20
FETCH_TIMEOUT = 10
ALLOWED_CONTENT_TYPES = ("text/", "application/json")


class IngestRefused(ValueError):
    """Fixed public refusals; never interpolates fetched content."""


def chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS,
               max_chunks: int = MAX_CHUNKS) -> list[str]:
    """Paragraph-aware chunks, each within max_chars, never exceeding max_chunks."""
    if not isinstance(text, str) or not text.strip():
        raise IngestRefused("Nothing to ingest")
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            chunks.append(paragraph)
            continue
        for start in range(0, len(paragraph), max_chars):
            chunks.append(paragraph[start:start + max_chars])
    merged: list[str] = []
    for chunk in chunks:
        if merged and len(merged[-1]) + len(chunk) + 2 <= max_chars:
            merged[-1] = merged[-1] + "\n\n" + chunk
        else:
            merged.append(chunk)
    if len(merged) > max_chunks:
        raise IngestRefused("Document exceeds the ingestion chunk budget")
    return merged


class _TextExtract(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.parts.append(data.strip())


def strip_html(html: str) -> str:
    parser = _TextExtract()
    try:
        parser.feed(html)
    except Exception as exc:  # malformed markup never aborts ingestion
        raise IngestRefused("Unreadable HTML document") from exc
    return "\n\n".join(parser.parts)


def check_addresses(addresses: list[str]) -> None:
    """Every resolved address must be global; anything else is refused."""
    if not addresses:
        raise IngestRefused("The host did not resolve")
    for address in addresses:
        try:
            parsed = ipaddress.ip_address(address)
        except ValueError as exc:
            raise IngestRefused("The host resolved to an invalid address") from exc
        if not parsed.is_global:
            raise IngestRefused("Refused: not a public address")


def resolve_public(host: str, resolver=socket.getaddrinfo) -> list[str]:
    if not host or len(host) > 253:
        raise IngestRefused("Invalid host")
    try:
        infos = resolver(host, None)
    except OSError as exc:
        raise IngestRefused("The host did not resolve") from exc
    addresses = sorted({info[4][0] for info in infos})
    check_addresses(addresses)
    return addresses


def validate_url(url: str) -> tuple[str, str, str, str]:
    """Returns (scheme, host, port, path); refuses credentials and odd shapes."""
    if not isinstance(url, str) or not 8 <= len(url) <= 2048:
        raise IngestRefused("Invalid URL")
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise IngestRefused("Only http(s) URLs are ingested")
    if parts.username or parts.password or parts.fragment:
        raise IngestRefused("URLs with embedded credentials are refused")
    port = parts.port or (443 if parts.scheme == "https" else 80)
    return parts.scheme, parts.hostname, port, parts.path or "/"


def fetch_public_text(url: str, resolver=socket.getaddrinfo,
                      max_bytes: int = MAX_FETCH_BYTES) -> tuple[str, str]:
    """Bounded, redirect-free text fetch from a public address only."""
    scheme, host, port, path = validate_url(url)
    resolve_public(host, resolver)
    connection = (HTTPSConnection(host, port, timeout=FETCH_TIMEOUT) if scheme == "https"
                  else HTTPConnection(host, port, timeout=FETCH_TIMEOUT))
    try:
        connection.request("GET", path, headers={"User-Agent": "enhanced-cognee-ingest/1",
                                                 "Accept": "text/*, application/json"})
        response = connection.getresponse()
        if response.status in (301, 302, 303, 307, 308):
            raise IngestRefused("Redirects are not followed during ingestion")
        if response.status != 200:
            raise IngestRefused("The source returned HTTP %d" % response.status)
        content_type = (response.getheader("Content-Type") or "").split(";")[0].strip().lower()
        if content_type and not content_type.startswith(ALLOWED_CONTENT_TYPES):
            raise IngestRefused("Only text sources are ingested")
        raw = response.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise IngestRefused("The source exceeds the ingestion size budget")
        text = raw.decode("utf-8", errors="replace")
    finally:
        connection.close()
    if "html" in content_type:
        text = strip_html(text)
    return text, content_type or "unknown"


def build_records(chunks: list[str], source: str, category: str, base_key: str) -> list[dict]:
    """Remember bodies with provenance; keys derive from the caller's base key."""
    if not 8 <= len(base_key) <= 100 or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", base_key):
        raise IngestRefused("Invalid ingestion base key")
    total = len(chunks)
    return [{
        "content": chunk,
        "idempotency_key": "%s-%04d-of-%04d" % (base_key, index + 1, total),
        "category": category,
        "metadata": {"origin": "ingest", "source": source[:300],
                     "chunk": index + 1, "chunks": total},
    } for index, chunk in enumerate(chunks)]
