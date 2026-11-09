"""Reproduce source-only verifier and renewal defects without side effects."""
import importlib.util
import io
import json
from pathlib import Path
import subprocess
from unittest.mock import patch

ROOT=Path.cwd()
OUT=Path(__file__).parent

def module(name,path):
    sp=importlib.util.spec_from_file_location(name,path)
    assert sp is not None and sp.loader is not None
    m=importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m

server=module('audit_mcp_server',ROOT/'integrations/hermes/enhanced_cognee_mcp/server.py')
request={'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'get_stats','arguments':{}}}
output=io.StringIO()
with patch.object(server,'api',return_value=(403,{'detail':'Invented refusal'})), patch('sys.stdin',io.StringIO(json.dumps(request)+'\n')), patch('sys.stdout',output):
    server.serve(server.apply_groups(server.handlers('invented-not-a-token'),'memory_read'))
reply=json.loads(output.getvalue())['result']
body=json.loads(reply['content'][0]['text'])
assert body.get('status_code')==403 and not reply.get('isError',False)
rows={'mcp_http_error_propagation':{'http_status':body['status_code'],'mcp_isError':reply.get('isError',False)}}
renewal=module('audit_installed_renewal',Path('/opt/enhanced-cognee-memory/fleet-renewal/renew_fleet_memory_tokens.py'))
with patch.object(renewal.subprocess,'run',return_value=subprocess.CompletedProcess([],1,stdout=b'{"complete":"false","expires_utc":"invented"}')):
    value=renewal.renew('invented-role')
assert value['complete'] is True
rows['renewal_bad_receipt_accepted']={'process_exit':1,'complete_input_type':'str','accepted_as_complete':value['complete']}
with patch.object(renewal.subprocess,'run',side_effect=subprocess.TimeoutExpired('invented-no-launch',180)):
    try:
        renewal.renew('invented-role')
    except subprocess.TimeoutExpired:
        rows['renewal_timeout']={'exception_escapes_profile_function':True}
# The next scheduled job invokes a writable interpreter, verified by metadata only.
unit=subprocess.check_output(['systemctl','cat','ec-hermes-memory-token-renew.service','ec-hermes-memory-token-renew.timer'],text=True)
(OUT/'renewal-units.txt').write_text(unit)
installed=Path('/opt/enhanced-cognee-memory/fleet-renewal/renew_fleet_memory_tokens.py')
source=ROOT/'integrations/hermes/deployment/renew_fleet_memory_tokens.py'
rows['installed_renewal_source']={'byte_identical':installed.read_bytes()==source.read_bytes(),
                                 'live_profile_discovery_count':len(renewal.profiles()),
                                 'source_only_unpinned_code_import': 'spec.loader.exec_module(module)' in source.read_text(),
                                 'installed_has_that_code_import': 'spec.loader.exec_module(module)' in installed.read_text()}
import os
import stat
interpreter=Path('/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/.venv-deployment/bin/python')
rows['root_job_writable_interpreter']={'uid':interpreter.stat().st_uid,'mode':oct(stat.S_IMODE(interpreter.stat().st_mode)),
                                      'user_can_write_target':os.access(interpreter.resolve(),os.W_OK),
                                      'user_can_replace_symlink':os.access(interpreter.parent,os.W_OK),
                                      'service_user_root':'User=root' in unit}
(OUT/'offline-secondary-probes.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows,indent=2))
