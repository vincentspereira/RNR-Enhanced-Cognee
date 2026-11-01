"""REA-only catalogue qualification using its pinned SDK's bounded stdio size."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import sys

PROTOCOL_SHA='415ef81f50ca0c209d9afd08c6a685f70c6ab951bbd5b672c5b32128bff52c07'
SDK_SHA='bc81a674f25546e2a631a5f3c9cb1829654bbfcdd40cb89823aab5fb719211e5'
REA=Path('/opt/hermes-runtime/programs/mcp-rea-30a10da51b212810')
REPLY_LIMIT=10*1024**2


def require(value):
    if not value:raise ValueError('rea_catalogue_probe_refused')


def protocol(path):
    require(re.fullmatch('/opt/hermes-runtime/programs/mcp-driver-[a-f0-9]{32}/probe.py',str(path)))
    raw=path.read_bytes();require(hashlib.sha256(raw).hexdigest()==PROTOCOL_SHA)
    value={'__name__':'retained_public_mcp_protocol','__file__':str(path)}
    exec(compile(raw,'<retained-public-mcp-protocol>','exec'),value)
    sdk=(REA/'node_modules/@modelcontextprotocol/server/dist/src-Cqbh3MYc.mjs').read_bytes()
    require(hashlib.sha256(sdk).hexdigest()==SDK_SHA
        and sdk.count(b'const STDIO_DEFAULT_MAX_BUFFER_SIZE = 10 * 1024 * 1024;')==1)
    # Only this finite REA reader uses the reviewed SDK budget. The installed
    # helpers, vendor code, schemas and Hermes guards remain unchanged.
    value['MAX_REPLY']=REPLY_LIMIT
    return value


def catalogue(module,client):
    observations={'phase':'initialize','catalogue_result_bytes':0}
    original=client.rpc
    def measured(method,params):
        observations['phase']=method
        value=original(method,params)
        if method=='tools/list':
            observations['catalogue_result_bytes']=len(json.dumps(value,separators=(',',':'),ensure_ascii=False).encode())
        return value
    client.rpc=measured
    names=module['handshake'](client)
    require(0<observations['catalogue_result_bytes']<=REPLY_LIMIT)
    return dict(complete=True,initialize_passed=True,tools_list_passed=True,tools_count=len(names),tools_called=0,
        binary_analysis_requested=False,reply_limit_bytes=REPLY_LIMIT,catalogue_result_bytes=observations['catalogue_result_bytes'])


def main():
    # The retained unit driver passes three public paths. The first is the old
    # PUBLIC PROTOCOL source, not a Filesystem package to execute.
    require(len(sys.argv)==4);source,rea,home=map(Path,sys.argv[1:])
    account=pwd.getpwuid(os.geteuid());fields=dict(row.split(':',1) for row in Path('/proc/self/status').read_text().splitlines())
    require(account.pw_name=='ecbot_5592956882ea9a13' and account.pw_uid>0
        and os.getresuid()==(account.pw_uid,)*3 and os.getresgid()==(account.pw_gid,)*3
        and set(os.getgroups())<={account.pw_gid} and fields['NoNewPrivs'].strip()=='1'
        and all(fields[k].strip()=='0000000000000000' for k in ('CapEff','CapAmb','CapInh'))
        and rea==REA and re.fullmatch('/run/ec-main-local-mcp-[a-f0-9]{32}',str(home)))
    invocation=os.environ.get('INVOCATION_ID','');require(re.fullmatch('[a-f0-9]{32}',invocation))
    env=dict(PATH='/usr/bin:/bin',HOME=str(home),LANG='C.UTF-8',XDG_CONFIG_HOME=str(home/'config'),XDG_CACHE_HOME=str(home/'cache'),
        GHIDRA_INSTALL_DIR='/opt/hermes-runtime/programs/rea-ghidra-490242e4126843ff',
        JAVA_HOME='/opt/hermes-runtime/programs/rea-java-8293b7cf98ee3589',DO_NOT_TRACK='1',NODE_ENV='production')
    os.environ.clear();os.environ.update(env);os.umask(0o077)
    result=dict(complete=False,invocation_id=invocation,cases={},real_profiles_read=False,credentials_read=False,
        model_called=False,memory_api_called=False,external_sends=0,full_main_tool_coverage_qualified=False)
    client=None
    try:
        module=protocol(source)
        client=module['Client'](['/usr/bin/node',str(REA/'node_modules/rea-agents/scripts/rea.mjs'),'mcp'],env,home)
        result['cases']['rea']=catalogue(module,client)
    except Exception as error:
        result['cases']['rea']=dict(complete=False,error_kind=type(error).__name__ if type(error).__name__ in
            {'ValueError','TimeoutError','OSError','PermissionError','JSONDecodeError','BrokenPipeError'} else 'other')
    finally:
        if client is not None:
            try:client.close()
            except Exception:result['cases']['rea']=dict(complete=False,error_kind='cleanup_failed')
    result['complete']=result['cases']['rea']['complete']
    print(json.dumps(result,sort_keys=True),flush=True)
    return 0 if result['complete'] else 1


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:
        print('{"complete":false,"category":"rea_catalogue_preflight_refused_no_secret_output"}',flush=True)
        raise SystemExit(1)
