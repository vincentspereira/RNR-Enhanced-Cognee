"""Restricted HTTP transport using Python's standard library only."""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener, HTTPSHandler


class MemoryTransportError(RuntimeError):
    def __init__(self, message, *, clarification_required=False, status_code=None):
        super().__init__(message)
        self.clarification_required = clarification_required
        self.status_code = status_code


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # A service redirect must never forward a profile credential.
        return None


class MemoryClient:
    def __init__(self, base_url: str, token: str, timeout: float = 3):
        parsed = urlsplit(base_url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
            raise ValueError("Configure an HTTP(S) service origin without credentials or a path")
        if parsed.scheme == "http" and parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError("A remote memory service requires HTTPS")
        if not token or not token.isascii() or any(c.isspace() for c in token):
            raise ValueError("A profile-scoped access token is required")
        if not 0 < timeout <= 10:
            raise ValueError("Memory timeout must be greater than zero and at most 10 seconds")
        self.base_url, self.token, self.timeout = base_url.rstrip("/"), token, timeout
        # Explicit origin, verified TLS, no ambient HTTP proxy or redirect routing.
        self.opener = build_opener(ProxyHandler({}), NoRedirect(), HTTPSHandler())

    def request(self, method: str, path: str, body: dict | None = None) -> dict:
        if not path.startswith("/v1/memories") and path != "/health/ready":
            raise ValueError("Unsupported memory endpoint")
        data = json.dumps(body, ensure_ascii=True).encode() if body is not None else None
        request = Request(self.base_url + path, data=data, method=method,
                          headers={"Authorization": "Bearer " + self.token, "Content-Type": "application/json"})
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                raw = response.read(262145)
                if len(raw) > 262144:
                    raise MemoryTransportError("Memory response exceeds its size budget")
                result = json.loads(raw)
                if not isinstance(result, dict):
                    raise MemoryTransportError("Invalid memory service response")
                return result
        except HTTPError as exc:
            clarify = False
            try:
                error = json.loads(exc.read(4096))
                clarify = isinstance(error, dict) and error.get("clarification_required") is True
            except (ValueError, OSError):
                pass
            finally:
                exc.close()
            raise MemoryTransportError(f"Memory request refused (HTTP {exc.code}); no success was acknowledged",
                                       clarification_required=clarify, status_code=exc.code) from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise MemoryTransportError("Memory service unavailable; retry with the same idempotency key") from None
