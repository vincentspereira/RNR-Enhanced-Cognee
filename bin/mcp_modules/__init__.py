"""
bin/mcp_modules/__init__.py
============================
MCP Tool Module Framework for Enhanced Cognee.

This package provides a register(mcp) protocol for decomposing the monolithic
`bin/enhanced_cognee_mcp_server.py` into focused, maintainable sub-modules.

Migration Strategy
------------------
The monolithic server (4 900+ lines) accumulates sections over time.
This package enables an incremental migration:

  Phase 5 (current):
    - Framework defined here.
    - Phase 2 and Phase 3 tools extracted as REFERENCE modules.
    - Monolithic server still self-contained (nothing imported from here).

  Phase 6+ (future):
    - New MCP tools are added to modules FIRST.
    - Monolithic server imports register() instead of defining tools inline.
    - Old tool groups gradually migrate from monolith -> module.

Module Contract
---------------
Every module must expose exactly one callable:

    def register(mcp: FastMCP) -> None:
        \"\"\"Register all tools in this module with the MCP server instance.\"\"\"
        @mcp.tool()
        async def my_tool(...) -> str:
            ...

Usage (future main server)
--------------------------
    from bin.mcp_modules.phase2_session_memory import register as p2_register
    from bin.mcp_modules.phase3_loaders import register as p3_register

    p2_register(mcp)
    p3_register(mcp)

Auto-discovery (advanced)
--------------------------
    import importlib
    import pkgutil
    import bin.mcp_modules as mcp_mods

    for finder, name, ispkg in pkgutil.iter_modules(mcp_mods.__path__):
        mod = importlib.import_module(f"bin.mcp_modules.{name}")
        if hasattr(mod, "register"):
            mod.register(mcp)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def discover_and_register(mcp: "FastMCP") -> list[str]:
    """
    Auto-discover all sub-modules that expose a register(mcp) function
    and call each one.  Returns list of registered module names.

    Call this from the main server ONLY if you have migrated tools out of
    the monolith - double-registration will cause errors.
    """
    import importlib
    import pkgutil
    import bin.mcp_modules as pkg

    registered = []
    for _, name, _ in pkgutil.iter_modules(pkg.__path__):
        if name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"bin.mcp_modules.{name}")
            if callable(getattr(mod, "register", None)):
                mod.register(mcp)
                registered.append(name)
        except Exception as exc:
            print(f"WARN Failed to register module {name}: {exc}")
    return registered


__all__ = ["discover_and_register"]
