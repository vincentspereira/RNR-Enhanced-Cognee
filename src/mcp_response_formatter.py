"""
Enhanced Cognee - MCP Response Formatter

Standardizes all MCP tool return values to consistent JSON format.

Format:
{
    "status": "success" | "error",
    "data": <any>,
    "error": <error message or null>,
    "timestamp": <ISO 8601 timestamp>
}
"""

import json
from typing import Any, Dict, Optional, Union
from datetime import datetime, timezone


def success_response(data: Any, operation: str = "operation") -> Dict[str, Any]:
    """
    Create a standardized success response.

    Args:
        data: Response data (can be any type)
        operation: Operation name for logging

    Returns:
        Standardized response dictionary
    """
    return {
        "status": "success",
        "data": data,
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": operation
    }


def error_response(error: str, operation: str = "operation") -> Dict[str, Any]:
    """
    Create a standardized error response.

    Args:
        error: Error message
        operation: Operation name for logging

    Returns:
        Standardized error response dictionary
    """
    return {
        "status": "error",
        "data": None,
        "error": error,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": operation
    }


def validation_error_response(error: str, operation: str = "operation") -> Dict[str, Any]:
    """
    Create a validation error response.

    Args:
        error: Validation error message
        operation: Operation name for logging

    Returns:
        Standardized validation error response dictionary
    """
    return {
        "status": "validation_error",
        "data": None,
        "error": f"Validation failed: {error}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": operation
    }


def authorization_error_response(error: str, operation: str = "operation") -> Dict[str, Any]:
    """
    Create an authorization error response.

    Args:
        error: Authorization error message
        operation: Operation name for logging

    Returns:
        Standardized authorization error response dictionary
    """
    return {
        "status": "authorization_error",
        "data": None,
        "error": f"Authorization failed: {error}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": operation
    }


def confirmation_required_response(
    operation: str,
    confirmation_id: str,
    details: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a confirmation required response.

    Args:
        operation: Operation requiring confirmation
        confirmation_id: Confirmation token ID
        details: Operation details

    Returns:
        Standardized confirmation required response dictionary
    """
    return {
        "status": "confirmation_required",
        "data": {
            "confirmation_id": confirmation_id,
            "operation": operation,
            "details": details
        },
        "error": f"Destructive operation requires confirmation: {operation}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": operation
    }


def format_response(response: Dict[str, Any]) -> str:
    """
    Format a response dictionary as JSON string.

    Args:
        response: Response dictionary from response functions

    Returns:
        Formatted JSON string
    """
    return json.dumps(response, indent=2, default=str)


def format_response_compact(response: Dict[str, Any]) -> str:
    """
    Format a response dictionary as compact JSON string.

    Args:
        response: Response dictionary from response functions

    Returns:
        Formatted compact JSON string (no indentation)
    """
    return json.dumps(response, separators=(',', ':'), default=str)


# Example usage and documentation
if __name__ == "__main__":
    # Success response example
    success = success_response(
        data={"memory_id": "abc123", "created": True},
        operation="add_memory"
    )
    print("Success Response:")
    print(format_response(success))

    # Error response example
    error = error_response(
        error="Database connection failed",
        operation="search_memories"
    )
    print("\nError Response:")
    print(format_response(error))

    # Validation error example
    val_error = validation_error_response(
        error="Invalid UUID format",
        operation="delete_memory"
    )
    print("\nValidation Error Response:")
    print(format_response(val_error))

    # Authorization error example
    auth_error = authorization_error_response(
        error="Admin privileges required",
        operation="create_backup"
    )
    print("\nAuthorization Error Response:")
    print(format_response(auth_error))

    # Confirmation required example
    conf_response = confirmation_required_response(
        operation="delete_memory",
        confirmation_id="confirm_1234567890",
        details={"memory_id": "abc123", "agent_id": "user123"}
    )
    print("\nConfirmation Required Response:")
    print(format_response(conf_response))
