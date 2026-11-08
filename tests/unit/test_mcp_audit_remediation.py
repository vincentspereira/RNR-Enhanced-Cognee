"""Offline regressions for the audited MCP contract; no real tokens or API."""
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('audited_mcp', ROOT / 'integrations/hermes/enhanced_cognee_mcp/server.py')
assert SPEC is not None and SPEC.loader is not None
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)

class McpAuditTests(unittest.TestCase):
    def run_rpc(self, messages, api_reply=(200, {'ready': True})):
        stream = io.StringIO(''.join(json.dumps(m)+'\n' for m in messages))
        output = io.StringIO()
        table = server.apply_groups(server.handlers('invented-placeholder'), 'memory_read,ingest,analysis')
        with patch.object(server, 'api', return_value=api_reply), patch('sys.stdin', stream), patch('sys.stdout', output):
            server.serve(table)
        return [json.loads(line) for line in output.getvalue().splitlines()]

    def call(self, name, args=None, ident=1):
        return {'jsonrpc':'2.0','id':ident,'method':'tools/call','params':{'name':name,'arguments':args or {}}}

    def test_http_refusal_is_an_mcp_error(self):
        replies = self.run_rpc([self.call('get_stats')], (403, {'detail':'Invented refusal'}))
        self.assertTrue(replies[0]['result'].get('isError'))

    def test_http_refusal_preserves_fixed_service_reason(self):
        replies=self.run_rpc([self.call('get_stats')],(403,{'detail':'Fixed scope refusal'}))
        self.assertIn('Fixed scope refusal',json.dumps(replies))
        self.assertTrue(replies[0]['result'].get('isError'))

    def test_malformed_params_does_not_kill_next_request(self):
        bad = {'jsonrpc':'2.0','id':1,'method':'tools/call','params':[1]}
        replies = self.run_rpc([bad,self.call('health',ident=2)])
        self.assertEqual(len(replies),2)
        self.assertIn('error',replies[0])
        self.assertEqual(replies[1]['id'],2)

    def test_invalid_arguments_do_not_echo_input(self):
        marker='invented-private-input'
        replies=self.run_rpc([self.call('recall',{'query':'valid','limit':marker})])
        self.assertNotIn(marker,json.dumps(replies))
        self.assertTrue(replies[0]['result'].get('isError'))

    def test_connection_uses_entity_contract(self):
        with patch.object(server,'api',return_value=(200,{})) as api:
            server.handlers('invented-placeholder')['get_related'][1]({'query':'calibration'})
        self.assertEqual(api.call_args.args[3],{'entity':'calibration'})

    def test_analysis_timeout_covers_server_model_deadline(self):
        class Response:
            status=200
            def read(self,n):return b'{}'
        class Connection:
            def __init__(self,*args,**kwargs): self.timeout=kwargs['timeout']; observed.append(self.timeout)
            def request(self,*args,**kwargs):pass
            def getresponse(self):return Response()
            def close(self):pass
        observed=[]
        with patch.object(server,'HTTPConnection',Connection):
            server.api('POST','/v1/memories/summarize','invented-placeholder',{})
        self.assertGreaterEqual(observed[0],60)

    def test_required_args_are_enforced_before_network(self):
        replies=self.run_rpc([self.call('get_memory',{})])
        self.assertTrue(replies[0]['result'].get('isError'))

if __name__=='__main__':unittest.main()
