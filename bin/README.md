# Enhanced Cognee Executables

This directory contains executable Python scripts for Enhanced Cognee.

## Main Scripts

### MCP Servers
- `enhanced_cognee_mcp_server.py` - Main MCP server for Claude Code integration
- `cognee_mcp_fallback.py` - Fallback MCP server implementation
- `cognee_mcp_universal.py` - Universal MCP wrapper
- `cognee_mcp_wrapper.py` - MCP wrapper for compatibility

### Installation & Setup
- `install.py` - Automated Python installer
- `setup_wizard.py` - Interactive configuration wizard
- `preflight.py` - Pre-flight checks before installation

### Utilities
- `run_tests.py` - Test runner script
- `fix_async_mock_warnings.py` - Fix async mock warnings
- `fix_datetime_warnings.py` - Fix datetime warnings

## Usage

Make sure the `bin/` directory is in your PATH or use absolute paths:

```bash
# Run MCP server
python bin/enhanced_cognee_mcp_server.py

# Run installation wizard
python bin/setup_wizard.py

# Run tests
python bin/run_tests.py
```

## MCP Configuration

Update your `~/.claude.json` configuration:

```json
{
  "mcpServers": {
    "cognee": {
      "command": "python",
      "args": [
        "/path/to/enhanced-cognee/bin/enhanced_cognee_mcp_server.py"
      ]
    }
  }
}
```
