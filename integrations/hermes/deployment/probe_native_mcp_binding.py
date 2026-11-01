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
    import datetime
    import yaml
    require(isinstance(raw, bytes) and 0 < len(raw) <= 262144 and b'\x00' not in raw,
            'config_size_or_nul')
    active = set()

    def validate(value, depth=0, path='config'):
        require(depth <= 32 and len(active) <= 4096, 'tree_bounds:' + path[:200])
        if isinstance(value, (dict, list)):
            require(id(value) not in active, 'tree_cycle:' + path[:200])
            active.add(id(value))
            try:
                if isinstance(value, dict):
                    require(all(isinstance(key, str) for key in value),
                            'tree_key_type:' + path[:200])
                    for key, child in value.items():
                        validate(key, depth + 1, (path + '/key')[:200])
                        validate(child, depth + 1, (path + '/' + key)[:200])
                else:
                    for index, child in enumerate(value):
                        validate(child, depth + 1, (path + '[%d]' % index)[:200])
            finally:
                active.discard(id(value))
        else:
            require(value is None or type(value) in {bool, int, str}
                    or type(value) is float and math.isfinite(value)
                    or type(value) in (datetime.date, datetime.datetime),
                    'scalar_type:' + path[:200])

    class UniqueLoader(yaml.SafeLoader):
        def construct_mapping(self, node, deep=False):
            self.flatten_mapping(node)
            result = {}
            for key_node, value_node in node.value:
                key = self.construct_object(key_node, deep=deep)
                require(isinstance(key, str) and key not in result,
                        'duplicate_or_nonstring_key')
                result[key] = self.construct_object(value_node, deep=deep)
            return result
    try:
        value = yaml.load(raw, Loader=UniqueLoader)
    except (yaml.YAMLError, UnicodeError):
        raise ValueError('config_yaml_unreadable') from None
    require(isinstance(value, dict), 'config_top_type')
    validate(value)
    return value


def config_candidates():
    """Config paths in the account's own Hermes layout, resolver-first.

    Mirrors hermes_constants: the OS account home (never the foreign process
    HOME a harness may set) plus its literal data-dir suffix, then any
    sibling .hermes* data directories.
    """
    account = Path(pwd.getpwuid(os.getuid()).pw_dir)
    suffix = os.environ.get('HERMES_DATA_DIR_SUFFIX', '')
    candidates = [account / ('.hermes' + suffix) / 'config.yaml']
    try:
        for entry in sorted(account.glob('.hermes*'))[:16]:
            candidate = entry / 'config.yaml'
            if candidate not in candidates:
                candidates.append(candidate)
    except OSError:
        pass
    return account, candidates


def resolve_config():
    account, candidates = config_candidates()
    diag = {'account_home': str(account), 'candidates': [], 'home_top_entries': []}
    try:
        diag['home_top_entries'] = sorted(entry.name for entry in account.iterdir())[:64]
    except OSError as exc:
        diag['home_top_entries'] = ['iter-error:' + type(exc).__name__]
    for candidate in candidates:
        row = {'path': str(candidate), 'exists': False, 'regular': False}
        try:
            info = candidate.lstat()
            row['exists'] = True
            row['regular'] = stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
        except OSError:
            pass
        diag['candidates'].append(row)
        if row['regular']:
            return candidate, candidate.read_bytes(), diag
    require(False, 'profile_config_not_found')


def definitions(raw):
    try:
        config = safe_config(raw)
    except ValueError as exc:
        raise ValueError('parse:' + str(exc)) from None
    servers = config.get('mcp_servers')
    if not isinstance(servers, dict):
        raise ValueError('mcp_servers_missing_keys:' + ','.join(sorted(
            key for key in config if isinstance(key, str)))[:240])
    if not 1 <= len(servers) <= 16:
        raise ValueError('mcp_servers_count:%d' % len(servers))
    rows, fetch, remotes = {}, None, []
    for name, row in servers.items():
        if not (isinstance(name, str) and 0 < len(name) <= 64):
            raise ValueError('server:name_invalid')
        if not isinstance(row, dict):
            raise ValueError('server:%s:not_mapping' % name[:64])
        if 'url' in row:
            # Remote HTTP MCP: binding means connecting to an external endpoint
            # with profile credentials, which needs an explicit owner gate.
            if not (isinstance(row.get('url'), str) and 0 < len(row['url']) <= 2048):
                raise ValueError('server:%s:url_invalid' % name[:64])
            headers = row.get('headers', {})
            require(isinstance(headers, dict) and all(
                isinstance(k, str) and isinstance(v, str) and 0 < len(k) <= 128
                for k, v in headers.items()), 'server:%s:headers_invalid' % name[:64])
            rows[name] = dict(name=name, kind='remote', url=row['url'],
                              headers=headers)
            remotes.append(name)
            continue
        command = row.get('command')
        if not (isinstance(command, str) and 0 < len(command) <= 256):
            raise ValueError('server:%s:command_invalid' % name[:64])
        args = row.get('args', [])
        if not (isinstance(args, list) and len(args) <= 32
                and all(isinstance(a, str) and len(a) <= 4096 for a in args)):
            raise ValueError('server:%s:args_invalid' % name[:64])
        env = row.get('env', {})
        if not (isinstance(env, dict) and all(isinstance(k, str) and isinstance(v, str)
                                              and 0 < len(k) <= 128 for k, v in env.items())):
            raise ValueError('server:%s:env_invalid' % name[:64])
        rows[name] = dict(name=name, kind='stdio', command=command, args=args, env=env)
        if any(FETCH_PACKAGE in arg for arg in [command] + args):
            require(fetch is None, 'multiple_fetch_definitions_refused')
            fetch = name
    return rows, fetch, remotes


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
    results, deferred = {}, []
    for name, row in sorted(servers.items()):
        if row['kind'] == 'remote':
            # Accounted, not launched: an external endpoint send needs the
            # owner's explicit qualification gate.
            deferred.append(name)
            results[name] = {'complete': True, 'binding': 'remote',
                             'remote_binding_qualified': False,
                             'deferred_reason': 'external_endpoint_requires_owner_gate'}
            continue
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
            entry['binding'] = 'stdio'
        except Exception as exc:
            if entry is None:
                entry = {'complete': False, 'binding': 'stdio', 'resolved_via': None,
                         'initialize_passed': False, 'tools_list_passed': False,
                         'tools_count': 0, 'private_denials': 0, 'env_key_count': 0}
                if row.get('env') is not None:
                    entry['env_key_count'] = len(row['env'])
            entry['error_kind'] = type(exc).__name__ if type(exc).__name__ in {
                'ValueError', 'TimeoutError', 'OSError', 'PermissionError',
                'JSONDecodeError', 'BrokenPipeError'} else 'other'
        results[name] = entry
    return results, deferred


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


def _first_json_body(raw: bytes):
    """Parse the first JSON-RPC payload: plain JSON or an SSE data event."""
    text = raw.decode('utf-8', 'replace')
    for line in text.splitlines():
        if line.startswith('data:'):
            return json.loads(line[5:].strip())
    return json.loads(text)


def _remote_rpc(connection, path, payload, headers, session, timeout):
    body = json.dumps(payload, separators=(',', ':')).encode()
    request = dict(headers)
    request['Content-Type'] = 'application/json'
    request['Accept'] = 'application/json, text/event-stream'
    if session:
        request['Mcp-Session-Id'] = session
    connection.request('POST', path, body, request)
    response = connection.getresponse()
    raw = response.read(262145)
    if response.status != 200 or len(raw) > 262144:
        raise ValueError('remote_http_%d' % response.status)
    return response, _first_json_body(raw)


def remote_catalogue(url, headers, timeout=25):
    """Initialize a streamable-HTTP MCP server and count its tools.

    Endpoint URLs and header values stay in memory; the receipt carries
    names, counts and error kinds only."""
    from http.client import HTTPSConnection, HTTPConnection
    from urllib.parse import urlsplit
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname:
        raise ValueError('remote_url_invalid')
    connection = (HTTPSConnection(parts.hostname, parts.port or 443, timeout=timeout)
                  if parts.scheme == 'https'
                  else HTTPConnection(parts.hostname, parts.port or 80, timeout=timeout))
    path = parts.path or '/'
    if parts.query:
        path += '?' + parts.query
    session = ''
    try:
        import uuid as _uuid
        response, init = _remote_rpc(connection, path, {
            'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
            'params': {'protocolVersion': '2024-11-05', 'capabilities': {},
                       'clientInfo': {'name': 'enhanced-cognee-qualification',
                                      'version': '1'}}}, headers, session, timeout)
        session = response.getheader('Mcp-Session-Id') or ''
        if not isinstance(init, dict) or init.get('id') != 1 or 'result' not in init:
            raise ValueError('remote_initialize_refused')
        try:
            connection.request('POST', path, json.dumps({
                'jsonrpc': '2.0', 'method': 'notifications/initialized'
            }).encode(), {'Content-Type': 'application/json',
                          'Accept': 'application/json, text/event-stream',
                          **({'Mcp-Session-Id': session} if session else {}), **headers})
            connection.getresponse().read(4096)
        except Exception:
            pass
        _, listing = _remote_rpc(connection, path, {
            'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list', 'params': {}},
            headers, session, timeout)
        result = (listing or {}).get('result') or {}
        tools = result.get('tools')
        if not isinstance(tools, list) or not 1 <= len(tools) <= 2048:
            raise ValueError('remote_catalogue_invalid')
        return {'initialize_passed': True, 'tools_count': len(tools)}
    finally:
        connection.close()


def run_remote_catalogue(servers):
    results = {}
    for name, row in sorted(servers.items()):
        if row['kind'] != 'remote':
            continue
        entry = {'complete': False, 'binding': 'remote', 'tools_count': 0,
                 'initialize_passed': False}
        try:
            found = remote_catalogue(row['url'], row['headers'])
            entry.update(found, complete=True)
        except Exception as exc:
            entry['error_kind'] = type(exc).__name__ if type(exc).__name__ in {
                'ValueError', 'TimeoutError', 'OSError', 'PermissionError',
                'JSONDecodeError'} else 'other'
        results[name] = entry
    return results


def main():
    stage, rundir, protocol_path = sys.argv[1:4]
    require(stage in {'catalogue', 'fetch-public', 'remote-catalogue'}
            and len(sys.argv) == 4)
    invocation = os.environ.get('INVOCATION_ID', '')
    require(re.fullmatch('[a-f0-9]{32}', invocation))
    scope = protocol(protocol_path)
    home = Path(rundir)
    require(home.is_dir() and home.stat().st_uid == os.getuid())
    os.environ['HERMES_DISABLE_LAZY_INSTALLS'] = '1'
    path, raw, diag = resolve_config()
    servers, fetch, remotes = definitions(raw)
    if stage == 'catalogue':
        results, deferred = run_catalogue(servers, fetch, home, scope, dict(os.environ))
        complete = all(row['complete'] for row in results.values())
        print(json.dumps({'stage': stage, 'complete': complete, 'invocation_id': invocation,
            'config_path': str(path), 'config_sha256': hashlib.sha256(raw).hexdigest(),
            'fetch_server': fetch, 'definition_count': len(servers),
            'remote_definitions_deferred': deferred, 'servers': results}), flush=True)
        return 0 if complete else 1
    if stage == 'remote-catalogue':
        results = run_remote_catalogue(servers)
        complete = all(row['complete'] for row in results.values()) and bool(results)
        print(json.dumps({'stage': stage, 'complete': complete,
                          'invocation_id': invocation,
                          'remote_count': len(results), 'servers': results}), flush=True)
        return 0 if complete else 1
    require(fetch in servers)
    result = run_fetch_public(servers[fetch], fetch, home, scope, dict(os.environ))
    result['invocation_id'] = invocation
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        detail = str(exc)[:200] if isinstance(exc, ValueError) else ''
        diag = {}
        try:
            _, _, diag = resolve_config()
        except Exception:
            pass
        print(json.dumps({'stage': 'preflight', 'complete': False,
                          'error_kind': type(exc).__name__, 'detail': detail,
                          'diag': diag}), flush=True)
        raise SystemExit(1)
