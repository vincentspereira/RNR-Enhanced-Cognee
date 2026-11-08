"""Offline ingestion security regressions; no service or network access."""
from __future__ import annotations
import json
import subprocess
from unittest.mock import Mock
import pytest
from src import ingestion as ing


def test_request_target_preserves_query_string():
    assert ing.validate_url('https://example.test/doc?q=a%2Fb&v=2')[3] == '/doc?q=a%2Fb&v=2'
    assert ing.validate_url('https://example.test/?q=1')[3] == '/?q=1'


def test_fetch_pins_validated_address_without_second_hostname_resolution(monkeypatch):
    dns_calls=[]
    connected=[]
    def resolver(*args):
        dns_calls.append(args)
        return [(2,1,6,'',('93.184.216.34',80))]
    class Socket:
        def settimeout(self,t):pass
        def connect(self,addr):connected.append(addr)
        def getpeername(self):return connected[-1]
        def close(self):pass
    sock=Socket()
    monkeypatch.setattr(ing.socket,'socket',lambda *a,**kw:sock)
    conn=ing.PinnedConnection('http','example.test',80,'93.184.216.34')
    conn.connect()
    assert connected==[('93.184.216.34',80)]
    assert not dns_calls
    assert conn.host=='example.test'


def test_peer_must_match_validated_public_address(monkeypatch):
    class Socket:
        def settimeout(self,t):pass
        def connect(self,addr):pass
        def getpeername(self):return ('127.0.0.1',80)
        def close(self):pass
    monkeypatch.setattr(ing.socket,'socket',lambda *a,**kw:Socket())
    with pytest.raises(ing.IngestRefused):
        ing.PinnedConnection('http','example.test',80,'93.184.216.34').connect()


def test_https_retains_original_certificate_name(monkeypatch):
    wrapped=[]
    class Socket:
        def settimeout(self,t):pass
        def connect(self,addr):pass
        def getpeername(self):return ('93.184.216.34',443)
        def close(self):pass
    class Context:
        def wrap_socket(self,sock,*,server_hostname):wrapped.append(server_hostname);return sock
    monkeypatch.setattr(ing.socket,'socket',lambda *a,**kw:Socket())
    monkeypatch.setattr(ing.ssl,'create_default_context',lambda:Context())
    ing.PinnedConnection('https','example.test',443,'93.184.216.34').connect()
    assert wrapped==['example.test']


def test_absolute_deadline_uses_isolated_worker_and_sanitises_timeout(monkeypatch):
    observed=[]
    def run(command,**kwargs):
        observed.append((command,kwargs))
        raise subprocess.TimeoutExpired(command,10,output=b'invented-private-content')
    monkeypatch.setattr(ing.subprocess,'run',run)
    with pytest.raises(ing.IngestRefused,match='deadline') as err:
        ing.fetch_public_text('https://example.test/doc')
    assert 'invented-private-content' not in str(err.value)
    assert observed[0][0][1:3]==['-I','-B']
    assert observed[0][1]['timeout']==ing.FETCH_TIMEOUT


def test_worker_result_is_bounded_and_validated(monkeypatch):
    monkeypatch.setattr(ing.subprocess,'run',lambda *a,**kw:subprocess.CompletedProcess([],0,json.dumps({'ok':True,'text':'invented public document','content_type':'text/plain'}).encode()))
    assert ing.fetch_public_text('https://example.test/doc')==('invented public document','text/plain')


def test_partial_ingestion_reports_only_acknowledged_ids():
    import asyncio
    class Store:
        def __init__(self):self.writes=[]
        async def remember(self, scope, **record):
            if self.writes:raise ValueError('invented-content-must-not-leak')
            self.writes.append(record)
            return {'id':'invented-first'}
    records=[{'content':'invented one'},{'content':'invented two'}]
    with pytest.raises(ing.IngestPartial) as caught:
        asyncio.run(ing.ingest_record_batch(Store(),object(),records))
    assert caught.value.record_ids==['invented-first']
    assert 'invented-content-must-not-leak' not in str(caught.value)


def test_mixed_public_private_dns_answers_fail_closed():
    with pytest.raises(ing.IngestRefused):ing.check_addresses(['93.184.216.34','127.0.0.1'])
