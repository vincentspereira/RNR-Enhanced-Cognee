"""Scoped library read regressions; fake database only."""
import asyncio
from pathlib import Path
import types
import unittest
from unittest.mock import AsyncMock

from src.memory_library import LibraryAccess
from src.memory_queries import MemoryQueries
from src.security.auth import Permission
from src.security.enterprise_auth import route_required_permission

class LibraryReadTests(unittest.TestCase):
    def test_library_get_requires_read_not_admin(self):
        for path in ['/v1/memories/library/','/v1/memories/library/membership']:
            self.assertEqual(route_required_permission('GET',path),Permission.MEMORY_READ)

    def test_library_mutation_still_requires_admin(self):
        for path in ['/v1/memories/library/membership','/v1/memories/invented-id/library']:
            self.assertEqual(route_required_permission('POST',path),Permission.MEMORY_ADMIN)

    def test_membership_is_scoped_to_callers_tenant_and_project(self):
        conn=types.SimpleNamespace(fetch=AsyncMock(return_value=[{'library':'team','can_publish':False}]))
        class Acquire:
            async def __aenter__(self):return conn
            async def __aexit__(self,*args):pass
        obj=LibraryAccess();obj.pool=types.SimpleNamespace(acquire=Acquire)
        scope=types.SimpleNamespace(tenant='invented_tenant',project='invented_project')
        result=asyncio.run(obj.library_membership(scope))
        self.assertEqual(result,{'memberships':[{'library':'team','can_publish':False}]})
        sql,*args=conn.fetch.call_args.args
        self.assertIn('tenant=$1',sql)
        self.assertIn('project=$2',sql)
        self.assertEqual(args,['invented_tenant','invented_project'])

    def test_shared_only_query_retains_existing_read_grants(self):
        conn=types.SimpleNamespace(fetch=AsyncMock(return_value=[]))
        class Acquire:
            async def __aenter__(self):return conn
            async def __aexit__(self,*args):pass
        obj=MemoryQueries();obj.pool=types.SimpleNamespace(acquire=Acquire)
        scope=types.SimpleNamespace(tenant='invented_tenant',project='invented_project',selected_capture=False)
        result=asyncio.run(obj.list_records(scope,shared_only=True,include_shared=True))
        sql,*args=conn.fetch.call_args.args
        self.assertIn('r.project<>$2',sql)
        self.assertIn('shared_memory.library_publications',sql)
        self.assertIn('p.version=r.version',sql)
        self.assertIn("r.state='active'",sql)
        self.assertEqual(result['results'],[])

if __name__=='__main__':unittest.main()
