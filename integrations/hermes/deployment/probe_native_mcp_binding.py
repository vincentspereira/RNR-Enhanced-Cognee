#!/usr/bin/env python3
"""Bind the profile's preserved MCP definitions through the native launcher.

Runs as the actual restricted main identity inside a hardened transient unit
and reads ONLY its own Hermes config, exactly as the native gateway would.
Stage 'catalogue' resolves every definition through the release's own
_resolve_stdio_command, launches it, handshakes, counts tools, and probes
only the Fetch private-address refusals. Stage 'fetch-public' additionally
performs the authorized public example.com retrieval in raw and default
modes. No secret value is echoed, logged or persisted; receipts carry
counts, flags and error kinds only.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path
import pwd
import re
import stat
import sys

RELEASE = Path('/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1')
PROTOCOL_SHA = '415ef81f50ca0c209d9afd08c6a685f70c6ab951bbd5b672c5b32128bff52c07'
PRIVATE_URLS = ('http://127.0.0.1/', 'http://169.254.169.254/')
PUBLIC_URL = 'https://example.com/'
REPLY_LIMIT = 10 * 1024 * 1024
FETCH_PACKAGE = 'mcp-server-fetch'


def require(value, category='native_mcp_binding_probe_refused'):
    if not value:
        raise ValueError(category)


def protocol(path):
    raw = Path(path).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == PROTOCOL_SHA)
    scope = {'__name__': 'verified_public_protocol', '__file__': str(path)}
    exec(compile(raw, '<verified-public-protocol>', 'exec'), scope)
    scope['MAX_REPLY'] = REPLY_LIMIT
    return scope


def private_denial(value, texts):
    if not isinstance(value, dict) or value.get('isError') is not True:
        return False
    return 'not a public address' in texts(value)


def safe_config(raw):
    """Bounded unique-key YAML load of the profile's own settings."""
    import yaml
    require(isinstance(raw, bytes) and 0 < len(raw) <= 262144 and b'\x00' not in raw)
    active = set()

    def validate(value, depth=0):
        require(depth <= 32 and len(active) <= 4096)
        if isinstance(value, (dict, list)):
            require(id(value) not in active)
            active.add(id(value))
            try:
                if isinstance(value, dict):
                    require(all(isinstance(key, str) for key in value))
                    for key, child in value.items():
                        validate(key, depth + 1)
                        validate(child, depth + 1)
                else:
                    for child in value:
                        validate(child, depth + 1)
            finally:
                active.discard(id(value))
        else:
            require(value is None or type(value) in {bool, int, str}
                    or type(value) is float and math.isfinite(value))

    class UniqueLoader(yaml.SafeLoader):
        def construct_mapping(self, node, deep=False):
            self.flatten_mapping(node)
            result = {}
            for key_node, value_node in node.value:
                key = self.construct_object(key_node, deep=deep)
                require(isinstance(key, str) and key not in result)
                result[key] = self.construct_object(value_node, deep=deep)
            return result
    try:
        value = yaml.load(raw, Loader=UniqueLoader)
    except (yaml.YAMLError, UnicodeError):
        raise ValueError('profile_config_yaml_refused') from None
    require(isinstance(value, dict))
    validate(value)
    return value


def own_config():
    account = pwd.getpwuid(os.getuid())
    path = Path(account.pw_dir) / '.hermes' / 'config.yaml'
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid())
    return path, path.read_bytes()


def definitions(raw):
    config = safe_config(raw)
    servers = config.get('mcp_servers')
    require(isinstance(servers, dict) and 1 <= len(servers) <= 8)
    rows, fetch = {}, None
    for name, row in servers.items():
        require(isinstance(row, dict) and isinstance(name, str) and 0 < len(name) <= 64)
        command = row.get('command')
        require(isinstance(command, str) and 0 < len(command) <= 256)
        args = row.get('args', [])
        require(isinstance(args, list) and len(args) <= 32
                and all(isinstance(a, str) and len(a) <= 4096 for a in args))
        env = row.get('env', {})
        require(isinstance(env, dict) and all(isinstance(k, str) and isinstance(v, str)
                                              and 0 < len(k) <= 128 for k, v in env.items()))
        rows[name] = dict(name=name, command=command, args=args, env=env)
        if any(FETCH_PACKAGE in arg for arg in [command] + args):
            require(fetch is None, 'multiple_fetch_definitions_refused')
            fetch = name
    return rows, fetch


def launch(row, env_base, home, scope):
    sys.path.insert(0, str(RELEASE / 'repo'))
    from tools.mcp_tool_config import _resolve_stdio_command
    merged = dict(env_base)
    merged.update(row['env'])
    resolved, merged = _resolve_stdio_command(row['command'], merged)
    entry = {'resolved_via': 'managed' if str(resolved).startswith(str(RELEASE))
             else ('passthrough' if resolved == row['command'] else 'path'),
             'complete': False, 'initialize_passed': False, 'tools_list_passed': False,
             'tools_count': 0, 'private_denials': 0, 'env_key_count': len(row['env'])}
    client = scope['Client']([resolved] + list(row['args']), merged, home)
    try:
        names = scope['handshake'](client)
        entry['initialize_passed'] = entry['tools_list_passed'] = True
        entry['tools_count'] = len(names)
        return client, entry, names
    except Exception:
        client.close()
        raise


def run_catalogue(servers, fetch, home, scope, env_base):
    results = {}
    for name, row in sorted(servers.items()):
        entry = None
        try:
            client, entry, names = launch(row, env_base, home, scope)
            try:
                if name == fetch:
                    for url in PRIVATE_URLS:
                        value = client.rpc('tools/call', {'name': 'fetch', 'arguments': {'url': url}})
                        require(private_denial(value, scope['texts']))
                        entry['private_denials'] += 1
            finally:
                client.close()
            entry['complete'] = True
        except Exception as exc:
            if entry is None:
                entry = {'complete': False, 'resolved_via': None, 'initialize_passed': False,
                         'tools_list_passed': False, 'tools_count': 0, 'private_denials': 0,
                         'env_key_count': len(row['env'])}
            entry['error_kind'] = type(exc).__name__ if type(exc).__name__ in {
                'ValueError', 'TimeoutError', 'OSError', 'PermissionError',
                'JSONDecodeError', 'BrokenPipeError'} else 'other'
        results[name] = entry
    return results


def run_fetch_public(row, fetch, home, scope, env_base):
    require(fetch is not None and row['name'] == fetch)
    result = {'stage': 'fetch-public', 'server': fetch, 'complete': False,
              'raw_passed': False, 'default_extraction_qualified': False, 'private_denials': 0}
    client, entry, names = launch(row, env_base, home, scope)
    try:
        require('fetch' in names)
        for url in PRIVATE_URLS:
            value = client.rpc('tools/call', {'name': 'fetch', 'arguments': {'url': url}})
            require(private_denial(value, scope['texts']))
            result['private_denials'] += 1
        value = client.rpc('tools/call', {'name': 'fetch', 'arguments':
            {'url': PUBLIC_URL, 'max_length': 5000, 'raw': True}})
        require(not value.get('isError')
                and 'example domain' in scope['texts'](value).lower())
        result['raw_passed'] = True
        value = client.rpc('tools/call', {'name': 'fetch', 'arguments':
            {'url': PUBLIC_URL, 'max_length': 5000}})
        require(not value.get('isError'))
        converted = scope['texts'](value)
        prefix = 'Contents of https://example.com/:'
        require(not converted.startswith('<error>Page failed to be simplified')
                and converted.startswith(prefix) and '<html' not in converted.lower()
                and bool(converted[len(prefix):].strip()))
        result['default_extraction_qualified'] = True
        result['complete'] = True
    finally:
        client.close()
    return result


def main():
    stage, rundir, protocol_path = sys.argv[1:4]
    require(stage in {'catalogue', 'fetch-public'} and len(sys.argv) == 4)
    invocation = os.environ.get('INVOCATION_ID', '')
    require(re.fullmatch('[a-f0-9]{32}', invocation))
    scope = protocol(protocol_path)
    home = Path(rundir)
    require(home.is_dir() and home.stat().st_uid == os.getuid())
    os.environ['HERMES_DISABLE_LAZY_INSTALLS'] = '1'
    path, raw = own_config()
    servers, fetch = definitions(raw)
    if stage == 'catalogue':
        results = run_catalogue(servers, fetch, home, scope, dict(os.environ))
        complete = all(row['complete'] for row in results.values())
        print(json.dumps({'stage': stage, 'complete': complete, 'invocation_id': invocation,
            'config_sha256': hashlib.sha256(raw).hexdigest(), 'fetch_server': fetch,
            'definition_count': len(servers), 'servers': results}), flush=True)
        return 0 if complete else 1
    require(fetch in servers)
    result = run_fetch_public(servers[fetch], fetch, home, scope, dict(os.environ))
    result['invocation_id'] = invocation
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        print('{"stage":"preflight","complete":false,"error_kind":"preflight_refused"}', flush=True)
        raise SystemExit(1)
