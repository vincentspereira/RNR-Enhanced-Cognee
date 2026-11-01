"""Narrow one inactive main candidate's filesystem root and select memory.

Only the exact reviewed filesystem MCP argument changes. Every other MCP,
model, platform, gateway and unrelated setting is preserved as structured data.
This transformation neither executes a server nor approves production use.
"""
from __future__ import annotations
import copy
from pathlib import Path

ORIGINAL_WORKSPACE = '/home/vincentspereira/agent-workspace'


def transform(config, home):
    if not isinstance(config, dict) or not isinstance(home, Path) or not home.is_absolute():
        raise ValueError('main_configuration_refused')
    if home.parent != Path('/var/lib/enhanced-cognee-profiles'):
        raise ValueError('fixed_isolated_main_home_required')
    if (not isinstance(config.get('gateway'), dict) or config['gateway'].get('multiplex_profiles') is not True
            or not isinstance(config.get('mcp_servers'), dict) or len(config['mcp_servers']) != 4
            or not isinstance(config.get('memory', {}), dict) or config.get('memory', {}).get('provider') is not None):
        raise ValueError('retained_main_configuration_required')
    result = copy.deepcopy(config)
    result['mcp_servers'] = copy.deepcopy(config['mcp_servers'])
    matches = []
    for name, server in result['mcp_servers'].items():
        if not isinstance(server, dict):
            raise ValueError('mcp_configuration_refused')
        args = server.get('args')
        if isinstance(args, list) and ORIGINAL_WORKSPACE in args:
            if (server.get('command') != 'npx' or args.count(ORIGINAL_WORKSPACE) != 1
                    or not any(isinstance(arg, str) and (arg == '@modelcontextprotocol/server-filesystem'
                               or arg.startswith('@modelcontextprotocol/server-filesystem@')) for arg in args)):
                raise ValueError('reviewed_filesystem_reference_required')
            matches.append(name)
    if len(matches) != 1:
        raise ValueError('unique_main_filesystem_reference_required')
    args = result['mcp_servers'][matches[0]]['args']
    args[args.index(ORIGINAL_WORKSPACE)] = str(home / '.hermes/workspace')
    result['memory'] = dict(copy.deepcopy(config.get('memory', {})), provider='enhanced_cognee')
    return result
