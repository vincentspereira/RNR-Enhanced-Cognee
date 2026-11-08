#!/usr/bin/env python3
"""Finite Fetch protocol/private-destination checks in a new empty HOME.

No private profile or memory is used. The optional public check reads only the
fixed example.com fixture, once raw and once through default HTML-to-Markdown
conversion; it is not a remote MCP or a native fleet acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

PROTOCOL_SHA = '415ef81f50ca0c209d9afd08c6a685f70c6ab951bbd5b672c5b32128bff52c07'


def protocol():
    path = Path(__file__).with_name('probe_main_local_mcp.py')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA:
        raise ValueError('public_protocol_changed')
    namespace = {'__name__': 'verified_public_protocol', '__file__': str(path)}
    exec(compile(raw, str(path), 'exec'), namespace)
    return namespace


def private_denial(value: dict) -> bool:
    if not isinstance(value, dict) or value.get('isError') is not True:
        return False
    content = value.get('content')
    if not isinstance(content, list):
        return False
    text = '\n'.join(row.get('text', '') for row in content
                     if isinstance(row, dict) and isinstance(row.get('text'), str))
    return 'not a public address' in text


def expected_html_body(text: str) -> bool:
    """Default-mode output must be converted Markdown of the fixed fixture.

    The check is structural, not textual: example.com's served copy has been
    reworded before, and with Node present Mozilla Readability moves the page
    heading into article metadata. Assert the server's own URL prefix, that
    HTML was actually converted away, and that the simplification failure
    marker is absent.
    """
    if not isinstance(text, str):
        return False
    if '<error>Page failed to be simplified from HTML</error>' in text:
        return False
    prefix = 'Contents of https://example.com/:'
    if not text.startswith(prefix):
        return False
    lowered = text.lower()
    if '<html' in lowered or '<body' in lowered or '<div' in lowered:
        return False
    return bool(text[len(prefix):].strip())


def exercise(executable: Path, home: Path, *, public: bool = False) -> dict:
    old = protocol()
    env = {'HOME': str(home), 'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8',
           'XDG_CACHE_HOME': str(home / 'cache'), 'DO_NOT_TRACK': '1'}
    client = old['Client']([str(executable), '-I', '-B', '-m', 'mcp_server_fetch'], env, home)
    result = {'complete': False, 'initialize_passed': False,
              'tools_list_passed': False, 'private_destination_denials': 0,
              'public_example_checked': public, 'public_example_passed': False,
              'html_markdown_extraction_qualified': False,
              'fetch_defaults_and_guards_unchanged': True,
              'profiles_read': False, 'memory_api_called': False,
              'model_called': False, 'native_hermes_binding_qualified': False,
              'fleet_launch_approved': False}
    try:
        result['phase'] = 'initialize_and_catalogue'
        names = old['handshake'](client)
        old['require'](names == {'fetch'})
        result.update(initialize_passed=True, tools_list_passed=True, tools_count=1)
        for url in ('http://127.0.0.1/', 'http://169.254.169.254/'):
            result['phase'] = 'private_destination_refusal'
            value = client.rpc('tools/call', {'name': 'fetch', 'arguments': {'url': url}})
            old['require'](private_denial(value))
            result['private_destination_denials'] += 1
        if public:
            result['phase'] = 'raw_public_example'
            value = client.rpc('tools/call', {'name': 'fetch', 'arguments': {'url': 'https://example.com/', 'max_length': 5000, 'raw': True}})
            old['require'](not value.get('isError') and 'example domain' in old['texts'](value).lower())
            result['public_example_passed'] = True
            result['public_example_mode'] = 'raw'
            result['phase'] = 'default_html_extraction'
            value = client.rpc('tools/call', {'name': 'fetch', 'arguments': {'url': 'https://example.com/', 'max_length': 5000}})
            old['require'](not value.get('isError'))
            old['require'](expected_html_body(old['texts'](value)))
            result['html_markdown_extraction_qualified'] = True
            result['html_default_mode_check'] = 'converted-markdown-structure-verified'
        result['complete'] = True
        result['phase'] = 'complete'
        return result
    except Exception as exc:
        result['error_kind'] = type(exc).__name__
        return result
    finally:
        client.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--output-parent', type=Path, required=True)
    parser.add_argument('--public-example', action='store_true')
    args = parser.parse_args()
    if os.getuid() == 0:
        raise SystemExit('ERR: this public build probe must not run as root')
    os.umask(0o077)
    home = Path(tempfile.mkdtemp(prefix='fetch-probe-', dir=args.output_parent.resolve(strict=True)))
    try:
        result = exercise(args.python.absolute(), home, public=args.public_example)
    except Exception as exc:
        result = {'complete': False, 'error_kind': type(exc).__name__,
                  'native_hermes_binding_qualified': False, 'fleet_launch_approved': False}
    result.update(evidence=str(home), qualification_surface='ordinary_owner_independent_public_fetch_build')
    (home / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
