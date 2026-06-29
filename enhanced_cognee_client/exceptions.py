"""
exceptions.py - RNR Enhanced Cognee client exception hierarchy.

All exceptions are ASCII-only (no Unicode symbols).
"""


class EnhancedCogneeError(Exception):
    """Base exception for all RNR Enhanced Cognee client errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message


class ConnectionError(EnhancedCogneeError):
    """Raised when the RNR Enhanced Cognee MCP server is unreachable.

    This wraps network-level failures such as refused connections,
    timeouts, and DNS resolution errors.
    """


class AuthError(EnhancedCogneeError):
    """Raised when the server rejects the supplied API key.

    HTTP 401 / 403 responses trigger this exception when an api_key
    has been configured on the client.
    """


class ToolError(EnhancedCogneeError):
    """Raised when a tool call returns an application-level error.

    The server accepted the request but the tool itself reported a
    failure (e.g. memory_id not found, validation failed).
    """
