"""Offline public MCP handshakes and invented filesystem operations only."""
from __future__ import annotations
import json
import os
from pathlib import Path
import pwd
import re
import selectors
import subprocess
import sys
import time

MAX_REPLY=2*1024**2


def require(value):
    if not value:raise ValueError('local_mcp_probe_refused')


class Client:
    def __init__(self,command,env,home):
        self.process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,env=env,cwd=home,start_new_session=True)
        self.sequence=0;self.pending=bytearray();self.deadline=time.monotonic()+90
        self.selector=selectors.DefaultSelector();self.selector.register(self.process.stdout,selectors.EVENT_READ)

    def send(self,value):
        raw=json.dumps(value,separators=(',',':')).encode()+b'\n';require(len(raw)<=8192)
        self.process.stdin.write(raw);self.process.stdin.flush()

    def response(self,ident):
        messages=0
        while time.monotonic()<self.deadline:
            if b'\n' not in self.pending:
                require(bool(self.selector.select(min(5,max(0,self.deadline-time.monotonic())))) or self.process.poll() is None)
                if not self.selector.select(0):continue
                chunk=os.read(self.process.stdout.fileno(),65536);require(bool(chunk));self.pending.extend(chunk)
                require(len(self.pending)<=MAX_REPLY)
                continue
            line,_,tail=self.pending.partition(b'\n');self.pending=bytearray(tail)
            if not line.strip():continue
            value=json.loads(line);messages+=1
            require(messages<=128 and isinstance(value,dict) and value.get('jsonrpc')=='2.0')
            # Never service unsolicited requests, sampling or elicitation.
            require('method' not in value or 'id' not in value)
            if value.get('id')!=ident:continue
            require('error' not in value and 'result' in value)
            return value['result']
        raise TimeoutError('local_mcp_probe_deadline')

    def rpc(self,method,params):
        require(method in {'initialize','tools/list','tools/call'})
        self.sequence+=1;self.send(dict(jsonrpc='2.0',id=self.sequence,method=method,params=params))
        return self.response(self.sequence)

    def close(self):
        self.selector.close()
        if self.process.stdin:self.process.stdin.close()
        try:self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=3)
        if self.process.stdout:self.process.stdout.close()


def handshake(client):
    result=client.rpc('initialize',dict(protocolVersion='2024-11-05',capabilities={},
        clientInfo=dict(name='enhanced-cognee-offline-qualification',version='1')))
    require(isinstance(result,dict) and isinstance(result.get('protocolVersion'),str)
        and isinstance(result.get('capabilities'),dict) and 'tools' in result['capabilities'])
    client.send(dict(jsonrpc='2.0',method='notifications/initialized'))
    result=client.rpc('tools/list',{})
    require(isinstance(result,dict) and isinstance(result.get('tools'),list) and 0<len(result['tools'])<=512
        and not result.get('nextCursor'))
    names=[]
    for tool in result['tools']:
        require(isinstance(tool,dict) and isinstance(tool.get('name'),str) and 0<len(tool['name'])<=128
            and isinstance(tool.get('inputSchema'),dict))
        names.append(tool['name'])
    require(len(names)==len(set(names)))
    return set(names)


def tool(client,name,arguments):
    require(name in {'list_allowed_directories','write_file','read_text_file','read_file'})
    value=client.rpc('tools/call',dict(name=name,arguments=arguments))
    require(isinstance(value,dict) and isinstance(value.get('content'),list))
    return value


def texts(value):
    return '\n'.join(row['text'] for row in value['content'] if isinstance(row,dict)
        and row.get('type')=='text' and isinstance(row.get('text'),str))


def exercise(program,bundle,env,home):
    workspace=home/'invented-workspace';workspace.mkdir(mode=0o700,exist_ok=True)
    entry=bundle/('node_modules/@modelcontextprotocol/server-filesystem/dist/index.js' if program=='filesystem'
        else 'node_modules/rea-agents/scripts/rea.mjs')
    command=['/usr/bin/node',str(entry)]+([str(workspace)] if program=='filesystem' else ['mcp'])
    client=Client(command,env,home)
    try:
        names=handshake(client)
        result=dict(complete=True,initialize_passed=True,tools_list_passed=True,tools_count=len(names),tools_called=0)
        if program=='filesystem':
            read='read_text_file' if 'read_text_file' in names else 'read_file'
            require({'list_allowed_directories','write_file',read}<=names)
            roots=tool(client,'list_allowed_directories',{});require(not roots.get('isError') and str(workspace) in texts(roots))
            path=workspace/'invented-cognee-probe.txt';marker='Invented offline MCP qualification only.'
            wrote=tool(client,'write_file',dict(path=str(path),content=marker));require(not wrote.get('isError'))
            recalled=tool(client,read,dict(path=str(path)));require(not recalled.get('isError') and marker in texts(recalled))
            denied=tool(client,read,dict(path='/etc/passwd'));require(denied.get('isError') is True)
            result.update(tools_called=4,invented_write_read_passed=True,outside_root_denied=True)
        else:
            # Catalog discovery only. Do not import/analyze a binary or repeat
            # the completed Ghidra/Java proof; no REA operation is requested.
            result.update(binary_analysis_requested=False)
        return result
    finally:client.close()


def main():
    require(len(sys.argv)==4);filesystem,rea,home=map(Path,sys.argv[1:])
    account=pwd.getpwuid(os.geteuid());fields=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines())
    require(account.pw_name=='ecbot_5592956882ea9a13' and os.getresuid()==(account.pw_uid,)*3 and account.pw_uid>0
        and os.getresgid()==(account.pw_gid,)*3 and set(os.getgroups())<={account.pw_gid}
        and fields['NoNewPrivs'].strip()=='1'
        and all(fields[k].strip()=='0000000000000000' for k in ('CapEff','CapAmb','CapInh'))
        and re.fullmatch('/run/ec-main-local-mcp-[a-f0-9]{32}',str(home))
        and re.fullmatch('/opt/hermes-runtime/programs/mcp-filesystem-[a-f0-9]{16}',str(filesystem))
        and re.fullmatch('/opt/hermes-runtime/programs/mcp-rea-[a-f0-9]{16}',str(rea)))
    invocation=os.environ.get('INVOCATION_ID','');require(re.fullmatch('[a-f0-9]{32}',invocation))
    env=dict(PATH='/usr/bin:/bin',HOME=str(home),LANG='C.UTF-8',XDG_CONFIG_HOME=str(home/'config'),XDG_CACHE_HOME=str(home/'cache'),
        GHIDRA_INSTALL_DIR='/opt/hermes-runtime/programs/rea-ghidra-490242e4126843ff',
        JAVA_HOME='/opt/hermes-runtime/programs/rea-java-8293b7cf98ee3589',DO_NOT_TRACK='1',NODE_ENV='production')
    os.environ.clear();os.environ.update(env);os.umask(0o077)
    result=dict(complete=False,invocation_id=invocation,cases={},real_profiles_read=False,credentials_read=False,
        model_called=False,memory_api_called=False,external_sends=0,full_main_tool_coverage_qualified=False)
    for program,bundle in [('filesystem',filesystem),('rea',rea)]:
        try:result['cases'][program]=exercise(program,bundle,env,home)
        except Exception as error:
            result['cases'][program]=dict(complete=False,error_kind=type(error).__name__ if type(error).__name__ in
                {'ValueError','TimeoutError','OSError','PermissionError','JSONDecodeError','BrokenPipeError'} else 'other')
    result['complete']=all(case['complete'] for case in result['cases'].values())
    print(json.dumps(result,sort_keys=True),flush=True)
    return 0 if result['complete'] else 1


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:
        print('{"complete":false,"category":"offline_local_mcp_probe_preflight_refused"}',flush=True)
        raise SystemExit(1)
