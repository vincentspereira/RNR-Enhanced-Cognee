"""Recognize explicit legacy tool failures at transport and audit boundaries."""
from __future__ import annotations


def tool_result_failed(value) -> bool:
    if getattr(value, "isError", False) is True:
        return True
    if isinstance(value, dict):
        return bool(value.get("error")) or value.get("status") in ("error", "failed", "failure") or tool_result_failed(value.get("result"))
    if isinstance(value, str):
        return value.lstrip().startswith(("ERR ", "ERR:", "Error:"))
    return False
