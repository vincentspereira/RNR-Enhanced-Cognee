"""Read-only, sanitized local route inventory for the human Hermes operator.

Read three fixed configuration files by default, or only the main config in
the explicit Z.ai Coding Plan inspection mode. Never read .env, conversations
or external secret stores. No Hermes startup, requests, model calls or writes.
These are declarations, not proof of route access, quota or served capabilities.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import pwd
import re
import stat
import sys
from urllib.parse import urlsplit


HOME = Path("/home/vincentspereira")
RELEASE = Path("/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1")
SOURCES = {"main": HOME / ".hermes/config.yaml",
           "earlier_test": HOME / ".hermes/profiles/enhanced-cognee-test/config.yaml",
           "earlier_test_two": HOME / ".hermes/profiles/enhanced-cognee-test-two/config.yaml"}
ZAI_ENDPOINTS = {"/api/coding/paas/v4": "coding_chat_completions",
                 "/api/anthropic": "coding_anthropic_messages",
                 "/api/v1": "coding_responses",
                 "/api/paas/v4": "general_api_not_coding"}


def local_origin(value):
    if not isinstance(value, str) or len(value) > 256 or not value.isascii() or any(c.isspace() for c in value):
        return None
    try:
        url = urlsplit(value)
        if (url.scheme not in {"http", "https"} or url.hostname not in {"127.0.0.1", "localhost", "::1"}
                or url.username is not None or url.password is not None or url.query or url.fragment
                or url.path not in {"", "/", "/v1", "/v1/"} or "?" in value or "#" in value):
            return None
        port = url.port
        if port is not None and not 1 <= port <= 65535:
            return None
        host = "[::1]" if url.hostname == "::1" else url.hostname
        return url.scheme + "://" + host + (":" + str(port) if port is not None else "") + url.path.rstrip("/")
    except ValueError:
        return None


def public_model(value):
    if (not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_./:+-]{0,159}", value)
            or value.lower().startswith(("sk-", "ghp_", "github_pat_", "xoxb-", "age-secret-"))
            or re.fullmatch(r"(?:AKIA|ASIA)[A-Z0-9]{16}", value)
            or "://" in value or value.count(".") > 6
            or re.search(r"[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}", value)):
        return None
    return value


def context_size(value):
    return value if type(value) is int and 1 <= value <= 16777216 else None


def zai_origin(value):
    if not isinstance(value, str) or len(value) > 256 or not value.isascii() or any(c.isspace() for c in value):
        return None
    try:
        url = urlsplit(value)
        path = url.path.rstrip("/")
        if (url.scheme != "https" or url.hostname != "api.z.ai" or url.port not in (None, 443)
                or url.username is not None or url.password is not None or url.query or url.fragment
                or "?" in value or "#" in value or path not in ZAI_ENDPOINTS):
            return None
        return "https://api.z.ai" + path, ZAI_ENDPOINTS[path]
    except ValueError:
        return None


def summarize_zai(config):
    if not isinstance(config, dict):
        raise ValueError("Main config must be a mapping")
    raw_model = config.get("model")
    selected = raw_model if isinstance(raw_model, dict) else {}
    current = public_model(selected.get("default") if selected else raw_model)
    entries = [("selected_model", selected)]
    custom = config.get("custom_providers", [])
    if isinstance(custom, list):
        entries.extend(("custom_" + str(i), row) for i, row in enumerate(custom[:32], 1))
    providers = config.get("providers", {})
    if isinstance(providers, dict):
        entries.extend(("provider_" + str(i), row) for i, row in enumerate(list(providers.values())[:32], 1))
    routes = []
    for label, row in entries:
        if not isinstance(row, dict):
            continue
        route = None
        for key in ("base_url", "baseUrl", "url", "api"):
            route = zai_origin(row.get(key))
            if route is not None:
                break
        if route is None:
            continue
        model_ids = []
        def admit(value):
            value = public_model(value)
            if value is not None and value.lower().startswith("glm-") and value not in model_ids and len(model_ids) < 16:
                model_ids.append(value)
        admit(row.get("default") if label == "selected_model" else row.get("model"))
        catalog = row.get("models", [])
        if isinstance(catalog, list):
            for value in catalog[:32]:
                admit(value.get("id", value.get("name")) if isinstance(value, dict) else value)
        elif isinstance(catalog, dict):
            for value in list(catalog)[:32]:
                admit(value)
        modes = {"chat_completions", "responses", "anthropic_messages", "openai-completions", "anthropic-messages"}
        mode = row.get("api_mode", row.get("api"))
        routes.append({"route": label, "base_url": route[0], "endpoint_kind": route[1],
                       "declared_glm_models": model_ids,
                       "configured_context_length": context_size(row.get("context_length")),
                       "api_mode": mode if isinstance(mode, str) and mode in modes else None,
                       "credential_reference_present": bool(row.get("key_env") or row.get("api_key_env") or row.get("keyEnv") or row.get("apiKeyEnv")),
                       "inline_credential_field_present": bool(row.get("api_key") or row.get("apiKey")),
                       "extra_headers_present": bool(row.get("extra_headers"))})
    selected_route = None
    for key in ("base_url", "baseUrl", "url", "api"):
        selected_route = zai_origin(selected.get(key))
        if selected_route is not None:
            break
    provider = selected.get("provider")
    builtin = isinstance(provider, str) and provider.lower() in {"zai", "glm", "z-ai", "z.ai", "zhipu"}
    return {"source": "main", "current_default_model": current,
            "current_default_matches_requested_test_model": isinstance(current, str) and current.casefold() == "glm-5.3-flash",
            "selected_provider_is_builtin_zai": builtin,
            "selected_explicit_zai_endpoint_kind": selected_route[1] if selected_route else None,
            "zai_routes": routes}


def summarize(config):
    if not isinstance(config, dict):
        return []
    selected = config.get("model") if isinstance(config.get("model"), dict) else {}
    entries = [("selected_model", selected, True)]
    custom = config.get("custom_providers", [])
    if isinstance(custom, list):
        entries.extend(("custom_" + str(i), row, False) for i, row in enumerate(custom[:32], 1))
    providers = config.get("providers", {})
    if isinstance(providers, dict):
        entries.extend(("provider_" + str(i), row, False) for i, row in enumerate(list(providers.values())[:32], 1))
    found = []
    for label, row, is_selected in entries:
        if not isinstance(row, dict):
            continue
        origin = local_origin(row.get("base_url", row.get("baseUrl")))
        if origin is None:
            continue
        models = []
        def admit(value, context=None):
            name = public_model(value)
            if name is not None and name not in {item["id"] for item in models} and len(models) < 16:
                models.append({"id": name, "configured_context_length": context_size(context)})
        admit(row.get("default") if is_selected else row.get("model"), row.get("context_length"))
        catalog = row.get("models", [])
        if isinstance(catalog, list):
            for item in catalog[:32]:
                if isinstance(item, str): admit(item, row.get("context_length"))
                elif isinstance(item, dict): admit(item.get("id", item.get("name")), item.get("context_length", row.get("context_length")))
        elif isinstance(catalog, dict):
            for name, item in list(catalog.items())[:32]:
                admit(name, item.get("context_length", row.get("context_length")) if isinstance(item, dict) else row.get("context_length"))
        if not is_selected and (selected.get("provider") == "custom:" + str(row.get("name", ""))
                                or local_origin(selected.get("base_url")) == origin):
            admit(selected.get("default"), selected.get("context_length", row.get("context_length")))
        mode = row.get("api_mode")
        found.append({"route": label, "base_url": origin, "models": models,
                      "api_mode": mode if isinstance(mode, str) and mode in {"chat_completions", "responses", "anthropic_messages"} else None,
                      "credential_reference_present": bool(row.get("key_env") or row.get("api_key") or row.get("api_key_env")),
                      "extra_headers_present": bool(row.get("extra_headers"))})
    return found


def read_config(path, uid):
    # Hold no-follow descriptors through all ancestors; refuse other ownership.
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
            info = os.fstat(fd)
            if info.st_uid not in {0, uid} or info.st_mode & 0o022:
                raise ValueError("Unsafe source directory")
        source = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        with os.fdopen(source, "rb") as handle:
            info = os.fstat(handle.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != uid or info.st_mode & 0o022
                    or info.st_size > 1048576):
                raise ValueError("Unsafe source file")
            raw = handle.read(1048577)
            after = os.fstat(handle.fileno())
            if (len(raw) != info.st_size or (info.st_size, info.st_mtime_ns, info.st_ctime_ns)
                    != (after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
                raise ValueError("Source changed")
        import yaml
        return yaml.safe_load(raw)
    finally:
        os.close(fd)


def main(*, zai_only=False):
    try:
        account = pwd.getpwuid(os.geteuid())
        if (account.pw_name != "vincentspereira" or account.pw_uid == 0 or Path(account.pw_dir) != HOME
                or os.environ.get("WSL_DISTRO_NAME") != "Ubuntu-Hermes"
                or not Path(sys.executable).resolve(strict=True).is_relative_to(RELEASE)):
            raise ValueError("Use the human Ubuntu-Hermes operator and protected Python")
        os.chdir(HOME)
        if type(zai_only) is not bool:
            raise ValueError("Use the fixed inspection mode")
        if zai_only:
            report = summarize_zai(read_config(SOURCES["main"], account.pw_uid))
            print(json.dumps({"complete": True, "inspection_mode": "zai_coding_plan",
                              "configured_routes_only": True, **report,
                              "model_defaults_changed": False, "env_or_secret_store_files_read": False,
                              "network_requests": False, "model_called": False, "files_changed": False},
                             indent=2, ensure_ascii=True))
            return
        sources = []
        for label, path in SOURCES.items():
            try:
                routes = summarize(read_config(path, account.pw_uid))
                sources.append({"source": label, "read": True, "local_routes": routes})
            except FileNotFoundError:
                sources.append({"source": label, "read": False, "reason": "not_present"})
            except Exception:
                sources.append({"source": label, "read": False, "reason": "unreadable_unsafe_or_invalid"})
        print(json.dumps({"complete": True, "configured_routes_only": True, "sources": sources,
                          "env_or_secret_store_files_read": False, "network_requests": False,
                          "model_called": False, "files_changed": False}, indent=2, ensure_ascii=True))
    except Exception:
        raise SystemExit("STOP: Local-route inspection incomplete; no private details printed or files changed.") from None


if __name__ == "__main__":
    raise SystemExit("Use the hash-verified read-only operator command.")
