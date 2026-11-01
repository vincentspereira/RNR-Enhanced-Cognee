"""Offline read-grant challenge: actual candidate predicate on synthetic SQLite.
This is not a PostgreSQL or installed service qualification.
"""
import asyncio
import importlib.util
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace

REPO=Path('/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/audit-remediation-worktree-20261101')
sys.path.insert(0,str(REPO))
from src.memory_queries import MemoryQueries
from src.memory_library import LibraryAccess


def test_shared_only_preserves_tenant_current_version_membership_and_publisher_gates():
    db=sqlite3.connect(':memory:')
    db.row_factory=sqlite3.Row
    db.create_function('now',0,lambda:'2026-11-01T00:00:00Z')
    db.execute("ATTACH DATABASE ':memory:' AS shared_memory")
    db.executescript('''
    CREATE TABLE shared_memory.records(id TEXT,tenant TEXT,project TEXT,state TEXT,expires_at TEXT,version INTEGER,updated_at TEXT);
    CREATE TABLE shared_memory.record_shares(tenant TEXT,project TEXT,record_id TEXT,target_project TEXT,version INTEGER);
    CREATE TABLE shared_memory.library_publications(tenant TEXT,project TEXT,record_id TEXT,library TEXT,version INTEGER);
    CREATE TABLE shared_memory.library_members(tenant TEXT,project TEXT,library TEXT,can_publish INTEGER);
    ''')
    fixtures=[('own','t','reader','active',None,1),('allowed','t','source','active',None,1),
              ('foreign-tenant','other','source','active',None,1),('stale','t','source','active',None,2),
              ('retracted','t','source','retracted',None,1),('expired','t','source','active','2000-01-01T00:00:00Z',1),
              ('no-publish','t','nonpublisher','active',None,1),('no-membership','t','source','active',None,1),
              ('direct-share','t','source','active',None,3)]
    db.executemany('INSERT INTO shared_memory.records VALUES(?,?,?,?,?,?,?)',[(*x,'2026-11-01') for x in fixtures])
    db.executemany('INSERT INTO shared_memory.library_members VALUES(?,?,?,?)',[
        ('t','reader','team',0),('t','source','team',1),('t','nonpublisher','team',0),('other','source','team',1)])
    db.executemany('INSERT INTO shared_memory.library_publications VALUES(?,?,?,?,?)',[
        (tenant,project,ident,'unapproved' if ident=='no-membership' else 'team',1)
        for ident,tenant,project,*_ in fixtures if ident not in ('own','direct-share')])
    db.execute('INSERT INTO shared_memory.record_shares VALUES(?,?,?,?,?)',('t','source','direct-share','reader',3))
    class Adapter:
        async def fetch(self,sql,*args):
            return db.execute(sql,args).fetchall()
    class Acquire:
        async def __aenter__(self):return Adapter()
        async def __aexit__(self,*args):pass
    obj=MemoryQueries()
    obj.pool=SimpleNamespace(acquire=Acquire)
    obj._decode=lambda row:{'id':row['id'],'project_id':row['project'],'content':'Invented','metadata':{},'provenance':{}}
    obj.shared_view=LibraryAccess.shared_view
    scope=SimpleNamespace(tenant='t',project='reader',selected_capture=False)
    try:
        result=asyncio.run(obj.list_records(scope,limit=50,offset=0,include_shared=True,shared_only=True))
        assert {r['id'] for r in result['results']}=={'allowed','direct-share'}
        assert all(r['shared'] is True for r in result['results'])
        db.execute("DELETE FROM shared_memory.library_members WHERE tenant='t' AND project='reader'")
        result=asyncio.run(obj.list_records(scope,limit=50,offset=0,include_shared=True,shared_only=True))
        assert {r['id'] for r in result['results']}=={'direct-share'}
    finally:
        db.close()
