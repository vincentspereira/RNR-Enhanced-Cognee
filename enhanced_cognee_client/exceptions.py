"""Compatibility exports for the canonical distributable SDK exception classes."""
from sdk_pkg.enhanced_cognee_client.exceptions import (
    AuthError, ConnectionError, EnhancedCogneeError, ToolError,
)

__all__ = ["AuthError", "ConnectionError", "EnhancedCogneeError", "ToolError"]
