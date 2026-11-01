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
import ssl
import subprocess
import sys
import json
from pathlib import Path
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


def validate_url(url: str) -> tuple[str, str, int, str]:
    """Returns (scheme, host, port, path); refuses credentials and odd shapes."""
    if not isinstance(url, str) or not 8 <= len(url) <= 2048:
        raise IngestRefused("Invalid URL")
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise IngestRefused("Only http(s) URLs are ingested")
    if parts.username or parts.password or parts.fragment:
        raise IngestRefused("URLs with embedded credentials are refused")
    port = parts.port or (443 if parts.scheme == "https" else 80)
    target = (parts.path or "/") + (("?" + parts.query) if parts.query else "")
    return parts.scheme, parts.hostname, port, target


class PinnedConnection(HTTPConnection):
    """Dial a validated numeric IP; retain original Host and TLS identity."""
    def __init__(self, scheme: str, host: str, port: int, address: str):
        super().__init__(host, port, timeout=FETCH_TIMEOUT)
        check_addresses([address])
        self.scheme, self.address = scheme, address

    def connect(self):
        family = socket.AF_INET6 if ipaddress.ip_address(self.address).version == 6 else socket.AF_INET
        sock = socket.socket(family, socket.SOCK_STREAM)
        try:
            sock.settimeout(self.timeout)
            sock.connect((self.address, self.port))
            peer = sock.getpeername()[0]
            check_addresses([peer])
            if ipaddress.ip_address(peer) != ipaddress.ip_address(self.address):
                raise IngestRefused("Refused: peer did not match admitted address")
            if self.scheme == "https":
                sock = ssl.create_default_context().wrap_socket(sock, server_hostname=self.host)
            self.sock = sock
        except BaseException:
            sock.close()
            raise


def _fetch_direct(url: str, resolver=socket.getaddrinfo,
                  max_bytes: int = MAX_FETCH_BYTES) -> tuple[str, str]:
    """Worker core; parent process enforces the total DNS/header/body deadline."""
    scheme, host, port, path = validate_url(url)
    addresses = resolve_public(host, resolver)
    connection = PinnedConnection(scheme, host, port, addresses[0])
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


def fetch_public_text(url: str, resolver=None,
                      max_bytes: int = MAX_FETCH_BYTES) -> tuple[str, str]:
    """A killable, isolated worker bounds even DNS and trickling HTTP headers.

    ``resolver`` is an explicit offline-test seam. The API never supplies it.
    subprocess.run kills and waits for its own child on deadline; no background
    DNS/body thread is left running. No URL or retrieved content is logged.
    """
    validate_url(url)
    if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_FETCH_BYTES:
        raise IngestRefused("Invalid ingestion size budget")
    if resolver is not None:
        return _fetch_direct(url, resolver=resolver, max_bytes=max_bytes)
    try:
        result = subprocess.run([sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--fetch-worker"],
            input=json.dumps({"url": url, "max_bytes": max_bytes}).encode(),
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=FETCH_TIMEOUT, check=False)
    except subprocess.TimeoutExpired:
        raise IngestRefused("Source fetch exceeded its total deadline") from None
    except OSError:
        raise IngestRefused("Source fetch worker is unavailable") from None
    # Worker stdout is generated only by the fixed bounded implementation.
    if len(result.stdout) > MAX_FETCH_BYTES * 8:
        raise IngestRefused("Source fetch worker exceeded its reply budget")
    try:
        value = json.loads(result.stdout)
    except (ValueError, TypeError):
        raise IngestRefused("Source fetch worker returned an invalid reply") from None
    if (result.returncode != 0 or not isinstance(value, dict) or value.get("ok") is not True):
        detail = value.get("detail") if isinstance(value, dict) else None
        # Only fixed worker refusals are surfaced, never OS errors or source text.
        allowed = {"Refused: not a public address", "The host did not resolve",
                   "Redirects are not followed during ingestion", "Only text sources are ingested",
                   "The source exceeds the ingestion size budget"}
        raise IngestRefused(detail if detail in allowed else "Source fetch was refused")
    text, content_type = value.get("text"), value.get("content_type")
    if not isinstance(text, str) or len(text) > max_bytes or not isinstance(content_type, str) or len(content_type) > 200:
        raise IngestRefused("Source fetch worker returned an invalid reply")
    return text, content_type


def _fetch_worker():
    try:
        body = json.loads(sys.stdin.buffer.read(8193))
        if not isinstance(body, dict) or set(body) != {"url", "max_bytes"}:
            raise IngestRefused("Invalid worker request")
        size = body["max_bytes"]
        if type(size) is not int or not 1 <= size <= MAX_FETCH_BYTES:
            raise IngestRefused("Invalid ingestion size budget")
        text, content_type = _fetch_direct(body["url"], max_bytes=size)
        print(json.dumps({"ok": True, "text": text, "content_type": content_type}, ensure_ascii=True))
    except IngestRefused as exc:
        print(json.dumps({"ok": False, "detail": str(exc)}, ensure_ascii=True))
    except Exception:
        print('{"ok":false,"detail":"Source fetch failed"}')

class IngestPartial(ValueError):
    """Explicit acknowledged progress; never include document content/errors."""
    def __init__(self, record_ids, chunks):
        super().__init__('Ingestion partially completed; retry the same base key')
        self.record_ids, self.chunks = list(record_ids), chunks


async def ingest_record_batch(store, scope, records):
    ids = []
    for record in records:
        try:
            row = await store.remember(scope, **record)
            ident = row.get('id') if isinstance(row, dict) else None
            if not isinstance(ident, str) or not ident:
                raise ValueError('Ingestion did not acknowledge a record')
            ids.append(ident)
        except Exception:
            if ids:
                raise IngestPartial(ids, len(records)) from None
            raise
    return ids


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


if __name__ == "__main__" and sys.argv[1:] == ["--fetch-worker"]:
    _fetch_worker()
