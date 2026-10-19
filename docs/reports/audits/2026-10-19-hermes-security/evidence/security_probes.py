"""Isolated audit reproductions: synthetic data, fake stores, no live services.

These assertions describe observed defects, not security acceptance tests.
Run with the repository virtualenv and the network-denying guard on PYTHONPATH.
"""
import ast
import asyncio
import json
import logging
import os
import pathlib
import sys
import time
import types
import typing
import tempfile
from unittest.mock import AsyncMock, Mock, patch

ROOT = pathlib.Path(os.environ.get('AUDIT_REPO_ROOT', pathlib.Path(__file__).resolve().parents[5]))
OUT = pathlib.Path(os.environ.get('AUDIT_OUTPUT_DIR') or tempfile.mkdtemp(prefix='rnr-cognee-audit-probes-'))
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
for key in list(os.environ):
    if any(word in key.upper() for word in ('KEY', 'TOKEN', 'SECRET', 'PASSWORD', 'CREDENTIAL')):
        os.environ.pop(key, None)
os.environ.update({
    'POSTGRES_PASSWORD': 'synthetic-audit-only',
    'NEO4J_PASSWORD': 'synthetic-audit-only',
    'ENHANCED_COGNEE_MODE': 'false',
    'COGNEE_TELEMETRY_ENABLED': '0',
    'TELEMETRY_DISABLED': '1',
    'ENHANCED_ENV': 'production',
    'ENHANCED_REQUIRE_TENANT': '1',
    'ENHANCED_JWT_SECRET': 'synthetic-audit-signing-key-32-bytes-minimum',
})
import dotenv
dotenv.load_dotenv = lambda *a, **k: False
import jwt
from fastapi.testclient import TestClient
from src.multi_tenant import TenantContext, get_tenant, sanitise_tenant_id
from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, MemoryEntry, SearchQuery
import src.enhanced_cognee_mcp as http_module
from src.security.enterprise_auth import tool_required_permission

logging.disable(logging.CRITICAL)
results = []


def record(name, details):
    results.append({'probe': name, 'status': 'OBSERVED', 'details': details})


def token(role='readonly', tenant='audit_a'):
    return jwt.encode({'sub': 'audit-reader', 'roles': [role], 'tenant': tenant,
                       'exp': int(time.time()) + 300}, os.environ['ENHANCED_JWT_SECRET'], algorithm='HS256')


class Conn:
    def __init__(self):
        self.sql = []

    async def execute(self, sql, *args):
        self.sql.append((sql, args, get_tenant()))
        return 'DELETE 1' if sql.lstrip().startswith('DELETE') else 'UPDATE 1'

    async def fetch(self, sql, *args):
        self.sql.append((sql, args, get_tenant()))
        return []

    async def fetchrow(self, sql, *args):
        self.sql.append((sql, args, get_tenant()))
        return None


class Pool:
    def __init__(self):
        self.conn = Conn()

    def acquire(self):
        conn = self.conn

        class Scope:
            async def __aenter__(self):
                return conn

            async def __aexit__(self, *args):
                return False
        return Scope()


async def registered_search_probe():
    tree = ast.parse((ROOT / 'bin/enhanced_cognee_mcp_server.py').read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'search_memories')
    fn.decorator_list = []
    pool = Pool()
    ns = {'Optional': typing.Optional, 'postgres_pool': pool,
          'sanitize_string': lambda value, **kw: value, 'validate_limit': lambda value, *args: value,
          'validate_agent_id': lambda value: value, 'performance_analytics': None,
          'ValidationError': ValueError, 'logger': logging.getLogger('probe')}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), '<audit-extracted-function>', 'exec'), ns)
    for tenant in ('audit_a', 'audit_b'):
        with TenantContext(tenant):
            await ns['search_memories']('synthetic-term')
    assert all('FROM shared_memory.documents\n' in q[0] for q in pool.conn.sql)
    record('registered_search_ignores_tenant', {'contexts': [q[2] for q in pool.conn.sql], 'table': 'shared_memory.documents'})


def http_scope_probes():
    srv = EnhancedCogneeMCPServer()
    captured = []

    async def add(entry):
        captured.append({'tenant': get_tenant(), 'agent_id': entry.agent_id})
        return 'synthetic-id'
    srv.add_memory = add
    client = TestClient(srv.app, raise_server_exceptions=False)
    headers = {'Authorization': 'Bearer ' + token('api_client'), 'X-Tenant-ID': 'audit_b'}
    response = client.post('/mcp/add_memory', headers=headers,
                           json={'content': 'synthetic', 'agent_id': 'another-agent'})
    assert response.status_code == 200, response.text
    assert captured == [{'tenant': 'audit_b', 'agent_id': 'another-agent'}]
    record('jwt_tenant_mismatch_and_agent_spoof_accepted', {'status': response.status_code, 'token_tenant': 'audit_a', 'observed': captured})

    backend = types.SimpleNamespace(call_tool=AsyncMock(return_value=([], {'result': 'synthetic-backend-only'})))
    with patch.object(http_module, '_ensure_bin_stack', AsyncMock()), patch.object(http_module, '_bin_mcp', backend), patch.object(http_module, '_bin_tool_names', {'remember', 'add_memory'}):
        headers = {'Authorization': 'Bearer ' + token(), 'X-Tenant-ID': 'audit_a'}
        bad = client.post('/tools/remember', headers=headers, json={'data': 'synthetic'})
        control = client.post('/tools/add_memory', headers=headers, json={'content': 'synthetic'})
        assert bad.status_code == 200, bad.text
        assert control.status_code == 403, control.text
        record('readonly_reaches_unmapped_mutating_tool', {'remember': bad.status_code, 'mapped_add_memory_control': control.status_code, 'remember_required_permission': str(tool_required_permission('remember'))})

    async def search(query):
        return []
    srv.search_memory = search
    os.environ['ENHANCED_MAX_PAYLOAD_BYTES'] = '128'
    body = json.dumps({'query': 'a' * 512}).encode()
    headers = {'Authorization': 'Bearer ' + token(), 'X-Tenant-ID': 'audit_a', 'Content-Type': 'application/json'}
    blocked = client.post('/memory/search', headers=headers, content=body)
    accepted = client.post('/memory/search', headers=headers, content=iter([body]))
    assert blocked.status_code == 413, blocked.text
    assert accepted.status_code == 200, accepted.text
    record('chunked_body_bypasses_payload_cap', {'body_bytes': len(body), 'cap': 128, 'fixed_length_status': blocked.status_code, 'chunked_status': accepted.status_code})
    os.environ.pop('ENHANCED_MAX_PAYLOAD_BYTES')
    client.close()


def dashboard_probe():
    import dashboard.dashboard_api as dashboard
    pool = Pool()
    with patch.object(dashboard, 'require_pg', return_value=pool):
        client = TestClient(dashboard.app, raise_server_exceptions=False)
        response = client.delete('/api/memories/00000000-0000-0000-0000-000000000001')
        assert response.status_code == 204, response.text
        assert 'DELETE FROM shared_memory.documents' in pool.conn.sql[0][0]
        record('dashboard_unauthenticated_delete', {'status': response.status_code, 'fake_database_calls': len(pool.conn.sql)})
        client.close()


async def storage_probes():
    srv = EnhancedCogneeMCPServer()
    srv.postgres_pool = Pool()
    srv.redis_client = types.SimpleNamespace(setex=AsyncMock(), delete=AsyncMock())
    srv.qdrant_client = types.SimpleNamespace(get_collection=Mock(), upsert=Mock(), search=Mock(return_value=[]))
    with TenantContext('audit_a'):
        entry = MemoryEntry(content='synthetic', agent_id='audit-agent', memory_category='dynamic_audit', embedding=[0.1, 0.2])
        await srv.add_memory(entry)
        await srv.search_memory(SearchQuery(query='synthetic', agent_id='audit-agent', memory_category='dynamic_audit', embedding=[0.1, 0.2]))
    write_collection = srv.qdrant_client.upsert.call_args.kwargs['collection_name']
    read_collection = srv.qdrant_client.search.call_args.kwargs['collection_name']
    assert write_collection != read_collection
    assert '__t__audit_a' in write_collection and '__t__audit_a' not in read_collection
    cache_key = srv.redis_client.setex.call_args.args[0]
    assert cache_key.startswith('memory:')
    record('vector_scope_mismatch_and_unscoped_cache', {'write_collection': write_collection, 'read_collection': read_collection, 'cache_key_prefix': 'memory:'})
    assert srv.postgres_pool.conn.sql[-1][1][2] == 'synthetic'
    record('normal_add_stores_plaintext', {'stored_content_equals_input': True})

    broken = EnhancedCogneeMCPServer()
    broken.postgres_pool = Pool()
    broken.qdrant_client = None
    broken.redis_client = types.SimpleNamespace(setex=AsyncMock(side_effect=RuntimeError('synthetic cache outage')))
    try:
        with TenantContext('audit_a'):
            await broken.add_memory(MemoryEntry(content='synthetic', agent_id='audit-agent', memory_category='dynamic_audit'))
    except Exception as error:
        assert any('INSERT INTO' in sql for sql, _, _ in broken.postgres_pool.conn.sql)
        record('cache_failure_after_database_commit', {'insert_observed': True, 'reported_failure_type': type(error).__name__})
    else:
        raise AssertionError('Expected post-insert error')


def encryption_probe():
    from src.encryption_manager import EncryptionManager
    first, second = EncryptionManager(), EncryptionManager()
    ciphertext = first.encrypt('synthetic')
    assert ciphertext.startswith('enc2:')
    assert second.decrypt(ciphertext) == ciphertext
    first._aesgcm = types.SimpleNamespace(encrypt=Mock(side_effect=RuntimeError('synthetic encryption fault')))
    assert first.encrypt('synthetic') == 'synthetic'
    record('ephemeral_keys_and_encrypt_failure_passthrough', {'fresh_instance_cannot_decrypt': True, 'encryption_error_returns_plaintext': True})


def python_sdk_probe():
    sys.path.insert(0, str(ROOT / 'sdk_pkg'))
    from enhanced_cognee_client.client import EnhancedCogneeClient
    client = EnhancedCogneeClient(api_key='synthetic-static-key')
    assert client._client.headers.get('authorization') == 'Bearer synthetic-static-key'
    assert client._client.headers.get('x-api-key') is None
    assert client._client.headers.get('x-tenant-id') is None
    record('python_sdk_static_key_header_mismatch', {'uses_bearer_for_api_key': True, 'tenant_header': False, 'scheme': client._base_url.split(':')[0]})
    asyncio.run(client.close())


if __name__ == '__main__':
    asyncio.run(registered_search_probe())
    http_scope_probes()
    dashboard_probe()
    asyncio.run(storage_probes())
    assert sanitise_tenant_id('audit-a') == sanitise_tenant_id('audit_a')
    record('tenant_identifier_collision', {'audit-a': sanitise_tenant_id('audit-a'), 'audit_a': sanitise_tenant_id('audit_a')})
    encryption_probe()
    python_sdk_probe()
    (OUT / 'security-probes.json').write_text(json.dumps(results, indent=2, ensure_ascii=True))
    print(json.dumps(results, indent=2, ensure_ascii=True))
