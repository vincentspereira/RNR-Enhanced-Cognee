# ADR-002: ASCII-Only Output Constraint

**Status:** Accepted
**Date:** 2026-01-18
**Deciders:** Enhanced Cognee maintainers

---

## Context

Enhanced Cognee runs as an MCP server that Claude Code invokes directly on the
developer's machine. On Windows, the default console encoding is cp1252, which maps
only the 256 characters of ISO-8859-1. Python's stdout defaults to this encoding
when a Windows terminal is detected.

During early development, MCP tool return strings used Unicode symbols for readability:
checkmarks (U+2713), cross marks (U+2717), warning triangles (U+26A0), and status
emoji. When Claude Code captured these strings and relayed them to the Windows
terminal, Python raised:

    UnicodeEncodeError: 'charmap' codec can't encode character '✓'
    in position 10: character maps to <undefined>

This exception crashed the MCP server process, making all tools unavailable until
manual restart. The failure was non-obvious to users because the error appeared in
the server log rather than in the Claude Code chat interface.

---

## Decision

All strings returned by MCP tools, all CLI output from the enhanced-cognee command,
and all log messages written to stdout or stderr must use only ASCII characters
(code points U+0000 through U+007F).

Status indicators use the following standard markers:

| Meaning | Marker    |
|---------|-----------|
| Success | [OK]      |
| Warning | [WARN]    |
| Error   | [ERR]     |
| Info    | [INFO]    |
| Done    | [DONE]    |

No Unicode arrows, checkmarks, crosses, emoji, or non-ASCII punctuation may appear
in any output path.

---

## Consequences

**Positive**
- The MCP server never crashes due to encoding errors on Windows.
- Output is readable in any terminal, including legacy cmd.exe windows.
- Log files stored by Windows tools remain searchable with basic grep equivalents.

**Negative**
- Output is visually plainer than Unicode-decorated alternatives.
- Contributors must remember the constraint and avoid copy-pasting symbols from other
  projects. Code reviews should check return strings in new MCP tool implementations.

---

## Alternatives Considered

**UTF-8 with BOM marker**
Setting the output stream to UTF-8 with a BOM at the start of the file or stream
can force Windows to interpret the byte sequence correctly. Rejected because it
requires modifying the server bootstrap before any MCP library imports take place,
and some Windows terminal versions still misinterpret the encoding declaration.

**Force PYTHONIOENCODING=utf-8 via environment variable**
Setting PYTHONIOENCODING=utf-8 in the MCP server launch environment would override
cp1252. Rejected because the MCP server is launched by Claude Code, which may not
propagate arbitrary environment variables, and because the fix depends on the
caller rather than the server itself.
