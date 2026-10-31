"""Stage D family-1 ingestion tests (pure helpers, invented fixtures)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / 'src'


def load(name):
    spec = importlib.util.spec_from_file_location(name, SRC / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ing = load('ingestion')


def test_chunk_text_respects_paragraphs_and_bounds():
    text = "\n\n".join("paragraph %d " % i + "word " * 30 for i in range(5))
    chunks = ing.chunk_text(text)
    assert 1 <= len(chunks) <= ing.MAX_CHUNKS
    assert all(len(chunk) <= ing.MAX_CHUNK_CHARS for chunk in chunks)
    assert chunks[0].startswith("paragraph 0")
    huge = "paragraph " * 10000  # 100k chars -> 50 chunks, over the 32 budget
    with pytest.raises(ing.IngestRefused):
        ing.chunk_text(huge)
    with pytest.raises(ing.IngestRefused):
        ing.chunk_text("   ")


def test_chunk_text_splits_oversized_paragraphs():
    paragraph = "x" * (ing.MAX_CHUNK_CHARS * 3 + 5)
    chunks = ing.chunk_text(paragraph)
    assert len(chunks) == 4
    assert all(len(chunk) <= ing.MAX_CHUNK_CHARS for chunk in chunks)
    assert "".join(part.strip(" ") for part in chunks).startswith("xxxx")


def test_strip_html_removes_scripts_and_keeps_text():
    html = "<html><body><h1>Title</h1><script>bad()</script>" \
           "<p>First paragraph.</p><style>.x{}</style><p>Second.</p></body></html>"
    text = ing.strip_html(html)
    assert "Title" in text and "First paragraph." in text and "Second." in text
    assert "bad()" not in text and ".x{}" not in text


def test_public_address_guard_refuses_every_non_global_address():
    for bad in ("127.0.0.1", "10.1.2.3", "192.168.1.4", "169.254.169.254",
                "::1", "fd00::1", "172.16.0.1", "0.0.0.0"):
        with pytest.raises(ing.IngestRefused, match="not a public address"):
            ing.check_addresses([bad])
    ing.check_addresses(["93.184.216.34", "2606:2800:220:1:248:1893:25c8:1946"])
    with pytest.raises(ing.IngestRefused):
        ing.check_addresses([])


def test_resolve_public_uses_injected_resolver():
    def fake_resolver(host, port):
        return [(0, 0, 0, "", ("93.184.216.34", 0))]
    assert ing.resolve_public("example.test", fake_resolver) == ["93.184.216.34"]

    def private(host, port):
        return [(0, 0, 0, "", ("10.0.0.5", 0))]
    with pytest.raises(ing.IngestRefused):
        ing.resolve_public("internal.test", private)

    def doc_range(host, port):
        return [(0, 0, 0, "", ("203.0.113.10", 0))]
    with pytest.raises(ing.IngestRefused):
        ing.resolve_public("documentation.test", doc_range)


def test_validate_url_refuses_credentials_and_odd_shapes():
    scheme, host, port, path = ing.validate_url("https://example.com/a?b=1")
    assert (scheme, host, port) == ("https", "example.com", 443)
    for bad in ("ftp://example.com/x", "https://user:pw@example.com/",
                "https://example.com/#frag", "not a url", ""):
        with pytest.raises(ing.IngestRefused):
            ing.validate_url(bad)


def test_build_records_shape_and_keys():
    records = ing.build_records(["alpha", "beta"], "https://example.test/doc",
                                "research", "pilot-20261031")
    assert [r["idempotency_key"] for r in records] == [
        "pilot-20261031-0001-of-0002", "pilot-20261031-0002-of-0002"]
    for record in records:
        assert record["metadata"]["origin"] == "ingest"
        assert record["metadata"]["chunks"] == 2
        assert record["metadata"]["source"].startswith("https://example.test")
        assert record["category"] == "research"
    for bad_key in ("short", "-nope", "UPPER", "x" * 101):
        with pytest.raises(ing.IngestRefused):
            ing.build_records(["a"], "s", "c", bad_key)
