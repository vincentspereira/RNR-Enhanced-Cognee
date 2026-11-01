"""Real route integration with invented stores, no backend/service startup."""
import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock
from starlette.requests import Request
from src.memory_api import create_app, IngestRequest
from src.security.enterprise_auth import Principal
from src.security.auth import Role

class ApiIntegrationTests(unittest.TestCase):
    def request(self):
        principal=Principal(subject='owner',role=Role.API_CLIENT,tenant_id='invented_tenant',claims={'project_id':'test_project'})
        return Request({'type':'http','state':{'principal':principal}})
    def endpoint(self,app,path,method):
        found=[route.endpoint for route in app.routes if getattr(route,'path',None)==path and method in getattr(route,'methods',{})]
        self.assertTrue(found,'missing declared read API endpoint')
        return found[0]
    def test_scoped_library_membership_endpoint(self):
        store=SimpleNamespace(library_membership=AsyncMock(return_value={'memberships':[]}))
        app=create_app(store)
        result=asyncio.run(self.endpoint(app,'/v1/memories/library/membership','GET')(self.request()))
        self.assertEqual(result,{'memberships':[]})
        self.assertEqual(store.library_membership.call_args.args[0].project,'test_project')
    def test_shared_read_endpoint_uses_shared_only_grant_query(self):
        store=SimpleNamespace(list_records=AsyncMock(return_value={'results':[]}))
        app=create_app(store)
        result=asyncio.run(self.endpoint(app,'/v1/memories/library/','GET')(self.request(),limit=50,offset=0))
        self.assertEqual(result,{'results':[]})
        self.assertTrue(store.list_records.call_args.kwargs['shared_only'])
        self.assertTrue(store.list_records.call_args.kwargs['include_shared'])
    def test_partial_ingest_returns_explicit_non_success_receipt(self):
        class Store:
            count=0
            async def remember(self,scope,**kwargs):
                self.count+=1
                if self.count==2:raise ValueError('invented private exception')
                return {'id':'invented-first'}
        store=Store();app=create_app(store)
        body=IngestRequest(text='a'*2000+'\n\n'+'b'*2000,base_key='audit-unique')
        result=asyncio.run(self.endpoint(app,'/v1/memories/ingest','POST')(body,self.request()))
        self.assertEqual(result.status_code,503)
        self.assertIn(b'invented-first',result.body)
        self.assertNotIn(b'invented private exception',result.body)
        self.assertIn(b'"complete":false',result.body)

if __name__=='__main__':unittest.main()
