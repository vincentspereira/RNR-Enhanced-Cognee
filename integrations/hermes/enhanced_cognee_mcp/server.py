#!/usr/bin/env python3
"""Enhanced Cognee gateway memory MCP server (Stage C, API-backed).

Pure standard library: JSON-RPC over stdio (MCP 2024-11-05 subset) and a
restricted HTTP client to the protected memory API on loopback. The
profile's scoped token arrives via the environment (rendered by the
gateway's secret scope) and is never logged. Tool groups prune the
advertised registry; anything unlisted is never advertised. All output on
stdout is protocol JSON; diagnostics go to stderr, ASCII only.
"""
from __future__ import annotations

import json
import os
import re
import sys
from http.client import HTTPConnection
from pathlib import Path
from urllib.parse import urlencode

API_HOST = "127.0.0.1"
API_PORT = 28080
TOKEN_ENV = "ENHANCED_COGNEE_ACCESS_TOKEN"
MAX_LINE = 1 << 20
MAX_BODY = 262144
PROTOCOL = "2024-11-05"
SERVER_INFO = {"name": "enhanced-cognee-memory", "version": "1.0.0-stage-c"}

GROUPS = {
    "memory_read": (
        "recall", "get_memories", "get_memory", "get_memory_history",
        "get_related", "list_agents", "get_shared_memories",
        "library_membership", "get_stats", "health",
    ),
    "memory_write": (
        "remember", "update_memory", "forget_memory", "set_memory_sharing",
    ),
    "ingest": (
        "ingest_url", "ingest_text",
    ),
    # Deliberately absent from every group: administration stays with the
    # operator; write tools stay disabled for fleet roles (the memory
    # provider remains the single governed write path). Ingestion writes
    # flow through the API's reviewed ingestion endpoint with provenance.
}


def _schema(name, description, properties, required=()):
    return {"name": name, "description": description,
            "inputSchema": {"type": "object", "properties": properties,
                            "required": list(required), "additionalProperties": False}}


def _text(value):
    return {"content": [{"type": "text",
                         "text": json.dumps(value, ensure_ascii=True, sort_keys=True)}]}


def _error(message):
    return {"content": [{"type": "text", "text": json.dumps(
        {"error": message, "success_acknowledged": False}, ensure_ascii=True)}],
        "isError": True}


def api(method, path, token, body=None):
    """Bounded call to the protected API; returns (status, json-or-None)."""
    data = json.dumps(body, ensure_ascii=True).encode() if body is not None else None
    headers = {"Authorization": "Bearer " + token}
    if data is not None:
        headers["Content-Type"] = "application/json"
    connection = HTTPConnection(API_HOST, API_PORT, timeout=10)
    try:
        connection.request(method, path, data, headers)
        response = connection.getresponse()
        raw = response.read(MAX_BODY + 1)
        if len(raw) > MAX_BODY:
            return response.status, {"error": "memory response exceeded its size budget"}
        try:
            return response.status, json.loads(raw) if raw else None
        except ValueError:
            return response.status, {"error": "memory response was not JSON"}
    finally:
        connection.close()


def _ident(value):
    text = str(value)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", text):
        raise ValueError("invalid record identifier")
    return text


def _limit(value, default=5, ceiling=50):
    number = int(value) if value is not None else default
    if not 1 <= number <= ceiling:
        raise ValueError("limit out of range")
    return number


def _query(value):
    text = str(value or "").strip()
    if not 1 <= len(text) <= 2000:
        raise ValueError("query must be 1-2000 characters")
    return text


def handlers(token):
    """name -> (schema, callable(args) -> payload)."""

    def call(method, path, body=None, expect=200):
        status, payload = api(method, path, token, body)
        if status != expect:
            return {"error": "memory request refused (HTTP %d); no success was "
                             "acknowledged" % status, "status_code": status}
        return payload

    table = {}

    def tool(name, description, properties, required, fn):
        table[name] = (_schema(name, description, properties, required), fn)

    tool("recall", "Semantic recall from this profile's memory space (and "
         "reviewed shares).", {"query": {"type": "string"},
                               "limit": {"type": "integer"}},
         ("query",), lambda a: call("POST", "/v1/memories/recall",
                                    {"query": _query(a.get("query")),
                                     "limit": _limit(a.get("limit"), 5, 20),
                                     "include_shared": True}))
    tool("get_memories", "List this profile's memory records (newest first).",
         {"limit": {"type": "integer"}, "offset": {"type": "integer"},
          "category": {"type": "string"}}, (),
         lambda a: call("GET", "/v1/memories?" + urlencode({
             "limit": _limit(a.get("limit"), 10, 200),
             "offset": max(0, int(a.get("offset") or 0)),
             **({"category": str(a["category"])} if a.get("category") else {})})))
    tool("get_memory", "Read one memory record by id.",
         {"record_id": {"type": "string"}}, ("record_id",),
         lambda a: call("GET", "/v1/memories/" + _ident(a.get("record_id"))))
    tool("get_memory_history", "Version history of one memory record.",
         {"record_id": {"type": "string"}}, ("record_id",),
         lambda a: call("GET", "/v1/memories/" + _ident(a.get("record_id")) + "/history"))
    tool("get_related", "Entities/records connected to a query in this space.",
         {"query": {"type": "string"}}, ("query",),
         lambda a: call("POST", "/v1/memories/connections",
                        {"query": _query(a.get("query"))}))
    tool("list_agents", "Agents known to this memory space.", {}, (),
         lambda a: call("GET", "/v1/memories/agents"))
    tool("get_shared_memories", "Reviewed shared-library entries visible to "
         "this profile.", {}, (),
         lambda a: call("GET", "/v1/memories/library/"))
    tool("library_membership", "This profile's shared-library memberships.", {},
         (), lambda a: call("GET", "/v1/memories/library/membership"))
    tool("get_stats", "Status of this profile's memory space (counts only).",
         {}, (), lambda a: call("GET", "/v1/memories/status"))
    tool("health", "Liveness of the memory service.", {}, (),
         lambda a: call("GET", "/health/ready"))
    tool("remember", "Store a selected memory (write path; not enabled for "
         "fleet roles in Stage C).",
         {"content": {"type": "string"}}, ("content",),
         lambda a: call("POST", "/v1/memories", {"content": str(a.get("content"))[:8192]},
                        expect=None))
    tool("update_memory", "Correct an existing memory (write path; requires "
         "the expected version for the owner/version check).",
         {"record_id": {"type": "string"}, "expected_version": {"type": "integer"},
          "content": {"type": "string"}},
         ("record_id", "expected_version", "content"),
         lambda a: call("PATCH", "/v1/memories/" + _ident(a.get("record_id")),
                        {"expected_version": int(a.get("expected_version")),
                         "content": str(a.get("content"))[:65536]}))
    tool("forget_memory", "Retract a memory (safe retraction, history kept).",
         {"record_id": {"type": "string"}}, ("record_id",),
         lambda a: call("POST", "/v1/memories/" + _ident(a.get("record_id")) + "/retract", {}))
    tool("set_memory_sharing", "Change a memory's sharing policy (write path).",
         {"record_id": {"type": "string"}, "policy": {"type": "string"}},
         ("record_id", "policy"),
         lambda a: call("PUT", "/v1/memories/" + _ident(a.get("record_id")) + "/share",
                        {"policy": str(a.get("policy"))}))
    import uuid as _uuid

    def _ingest(body):
        body.setdefault("base_key", "mcp-" + _uuid.uuid4().hex[:20])
        return call("POST", "/v1/memories/ingest", body)

    tool("ingest_url", "Fetch a public text/HTML page and store its content "
         "in this profile's memory space with source provenance. Private "
         "addresses are refused.",
         {"url": {"type": "string"}, "title": {"type": "string"},
          "category": {"type": "string"}}, ("url",),
         lambda a: _ingest({"url": str(a.get("url")),
                            **({"title": str(a["title"])} if a.get("title") else {}),
                            **({"category": str(a["category"])}
                               if a.get("category") else {})}))
    tool("ingest_text", "Store a provided document/text in this profile's "
         "memory space, chunked with provenance.",
         {"text": {"type": "string"}, "title": {"type": "string"},
          "category": {"type": "string"}}, ("text",),
         lambda a: _ingest({"text": str(a.get("text")),
                            **({"title": str(a["title"])} if a.get("title") else {}),
                            **({"category": str(a["category"])}
                               if a.get("category") else {})}))
    return table


def apply_groups(table, spec):
    names = [name.strip() for name in spec.split(",") if name.strip()]
    if not names:
        raise SystemExit("ERR tool group selection refused: empty")
    unknown = [name for name in names if name not in GROUPS]
    if unknown:
        raise SystemExit("ERR tool group selection refused: " + ",".join(unknown))
    allowed = {tool for name in names for tool in GROUPS[name]}
    missing = sorted(allowed - table.keys())
    if missing:
        raise SystemExit("ERR tool group selection refused, missing tools: "
                         + ",".join(missing))
    return {name: table[name] for name in table if name in allowed}


def serve(table):
    for line in sys.stdin:
        if len(line) > MAX_LINE:
            continue
        text = line.strip()
        if not text:
            continue
        try:
            message = json.loads(text)
        except ValueError:
            continue
        if not isinstance(message, dict):
            continue
        method = message.get("method")
        identifier = message.get("id")
        if method in ("notifications/initialized",):
            continue
        if identifier is None:  # other notifications are ignored
            continue
        if method == "initialize":
            result = {"protocolVersion": PROTOCOL,
                      "capabilities": {"tools": {}}, "serverInfo": SERVER_INFO}
        elif method == "tools/list":
            result = {"tools": [schema for schema, _ in table.values()]}
        elif method == "tools/call":
            params = message.get("params") or {}
            entry = table.get(params.get("name"))
            if entry is None:
                result = _error("unknown tool for this group selection")
                print(json.dumps({"jsonrpc": "2.0", "id": identifier,
                                  "result": result}), flush=True)
                continue
            try:
                result = _text(entry[1](params.get("arguments") or {}))
            except ValueError as exc:
                result = _error(str(exc))
            except Exception:
                result = _error("memory call failed; no success was acknowledged")
        else:
            print(json.dumps({"jsonrpc": "2.0", "id": identifier,
                              "error": {"code": -32601,
                                        "message": "method not offered"}}), flush=True)
            continue
        print(json.dumps({"jsonrpc": "2.0", "id": identifier,
                          "result": result}, ensure_ascii=True), flush=True)


def main():
    token = os.environ.get(TOKEN_ENV, "")
    if not token or any(character.isspace() for character in token):
        print("ERR %s is not set for this profile; the memory tools stay "
              "unavailable." % TOKEN_ENV, file=sys.stderr)
        raise SystemExit(2)
    groups_spec = ""
    args = sys.argv[1:]
    if "--tool-groups" in args:
        index = args.index("--tool-groups")
        if index + 1 >= len(args):
            raise SystemExit("ERR --tool-groups needs a value")
        groups_spec = args[index + 1]
    table = handlers(token)
    if groups_spec:
        table = apply_groups(table, groups_spec)
        print("OK groups %s: %d tools advertised" % (groups_spec, len(table)),
              file=sys.stderr)
    serve(table)


if __name__ == "__main__":
    main()
