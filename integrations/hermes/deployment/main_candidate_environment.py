"""Align only the inactive main copy with its already qualified Coding route.

Preserve the model credential and every unrelated environment binding. The
only existing endpoint eligible for replacement is the public ZAI Coding
alias; arbitrary endpoints and conflicting keys still require review. The
caller retains the complete old environment before atomic publication.
"""
from __future__ import annotations
import io
import re
from urllib.parse import urlsplit

TARGET = 'https://open.bigmodel.cn/api/coding/paas/v4'
ALIAS = 'https://api.z.ai/api/coding/paas/v4'


def require(value):
    if not value:
        raise ValueError('main_candidate_environment_refused')


def prepare(raw, key_env, key, endpoint):
    from dotenv.parser import parse_stream
    require(isinstance(raw, bytes) and 0 < len(raw) <= 65536 and b'\x00' not in raw
            and endpoint == '/api/coding/paas/v4'
            and isinstance(key_env, str) and (key_env in {'GLM_API_KEY', 'ZAI_API_KEY', 'Z_AI_API_KEY'}
                or re.fullmatch(r'HERMES_CUSTOM_[A-Z0-9_]{1,100}_API_KEY', key_env)))
    require(isinstance(key, str) and 16 <= len(key) <= 4096
            and not any(char in key for char in '\r\n\x00'))
    rows = list(parse_stream(io.StringIO(raw.decode())))
    require(not any(row.error for row in rows))
    fields = {name: [row for row in rows if row.key == name] for name in (key_env, 'GLM_BASE_URL')}
    require(all(len(value) <= 1 for value in fields.values()))
    require(not fields[key_env] or fields[key_env][0].value == key)
    origin = fields['GLM_BASE_URL']
    if origin:
        value = origin[0].value
        require(isinstance(value, str) and value.rstrip('/') in {TARGET, ALIAS})
        parsed = urlsplit(value)
        require(not (parsed.username or parsed.password or parsed.query or parsed.fragment))
    parts = []
    for row in rows:
        text = row.original.string
        if row.key == 'GLM_BASE_URL' and row.value != TARGET:
            require(text.count(row.value) == 1)
            text = text.replace(row.value, TARGET, 1)
        parts.append(text)
    result = ''.join(parts).encode()
    missing = {}
    if not fields[key_env]: missing[key_env] = key
    if not origin: missing['GLM_BASE_URL'] = TARGET
    if missing:
        lines = [name + '="' + value.replace('\\', '\\\\').replace('"', '\\"') + '"\n'
                 for name, value in missing.items()]
        result += (b'' if result.endswith(b'\n') else b'\n') + ''.join(lines).encode()
    after = list(parse_stream(io.StringIO(result.decode())))
    require(len(result) <= 65536 and not any(row.error for row in after)
            and [(row.key, row.value) for row in rows if row.key not in {None, key_env, 'GLM_BASE_URL'}]
                == [(row.key, row.value) for row in after if row.key not in {None, key_env, 'GLM_BASE_URL'}]
            and [row.value for row in after if row.key == key_env] == [key]
            and [row.value for row in after if row.key == 'GLM_BASE_URL'] == [TARGET])
    return result
