#!/usr/bin/env python3
"""Read-only inspection of the live main profile's memory provider selection.

Runs as the actual restricted main identity and reads only its own Hermes
config, exactly like the native binding driver whose resolution and loader
it reuses through the pinned source. Reports the memory provider name, the
memory section key names, and the MCP definition names. No value, secret,
path argument or server definition body is ever emitted; nothing is written.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import sys

RELEASE = Path('/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1')
BINDING_DRIVER_SHA = 'a54f321c30b64924a3b72d0b779f90997ec89674f65e192d6643cd02c3e062d5'


def require(value, category='main_memory_selection_refused'):
    if not value:
        raise ValueError(category)


def binding_support(path):
    raw = Path(path).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == BINDING_DRIVER_SHA, 'binding_driver_pin')
    scope = {'__name__': 'verified_binding_support', '__file__': str(path)}
    exec(compile(raw, '<verified-binding-support>', 'exec'), scope)
    return scope


def memory_selection(config):
    memory = config.get('memory')
    if memory is None:
        return {'provider': None, 'selected': False, 'keys': []}
    require(isinstance(memory, dict), 'memory_section_not_mapping')
    provider = memory.get('provider')
    require(provider is None or (isinstance(provider, str) and 0 < len(provider) <= 64),
            'memory_provider_type')
    keys = sorted(key for key in memory if isinstance(key, str))
    return {'provider': provider, 'selected': provider == 'enhanced_cognee', 'keys': keys[:32]}


def main():
    stage, rundir, support_path = sys.argv[1:4]
    require(stage == 'inspect' and len(sys.argv) == 4)
    invocation = os.environ.get('INVOCATION_ID', '')
    require(re.fullmatch('[a-f0-9]{32}', invocation))
    support = binding_support(support_path)
    home = Path(rundir)
    require(home.is_dir() and home.stat().st_uid == os.getuid())
    path, raw, diag = support['resolve_config']()
    config = support['safe_config'](raw)
    servers = config.get('mcp_servers')
    require(isinstance(servers, dict) and 1 <= len(servers) <= 16, 'mcp_servers_shape')
    memory = memory_selection(config)
    print(json.dumps({'stage': stage, 'complete': True, 'invocation_id': invocation,
        'config_path': str(path), 'config_sha256': hashlib.sha256(raw).hexdigest(),
        'config_bytes': len(raw), 'memory': memory,
        'mcp_definition_count': len(servers),
        'mcp_definition_names': sorted(servers)[:16]}), flush=True)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        detail = str(exc)[:200] if isinstance(exc, ValueError) else ''
        print(json.dumps({'stage': 'preflight', 'complete': False,
                          'error_kind': type(exc).__name__, 'detail': detail}), flush=True)
        raise SystemExit(1)
