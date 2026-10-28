"""Run public Java/Ghidra in a network-isolated unit with an empty private HOME.

No real profile, REA server, credential, model or external platform is used.
The project imports only /usr/bin/true with analysis disabled and is retained.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def runtime_environment(java,home):
    # JVM user.home may come from passwd rather than HOME. Bind both to the
    # invented RuntimeDirectory; real profile paths are also kernel-denied.
    return dict(PATH=str(java/'bin')+':/usr/bin:/bin',HOME=str(home),JAVA_HOME=str(java),LANG='C.UTF-8',
        JAVA_TOOL_OPTIONS='-Duser.home='+str(home),XDG_CONFIG_HOME=str(home/'config'),
        XDG_CACHE_HOME=str(home/'cache'),GHIDRA_HEADLESS_MAXMEM='768M')


def main():
    if len(sys.argv)!=4:raise ValueError('program_probe_contract_refused')
    ghidra,java,home=map(Path,sys.argv[1:])
    if not (os.geteuid()>0 and re.fullmatch('/opt/hermes-runtime/programs/proof-ghidra-[a-f0-9]{32}',str(ghidra))
            and re.fullmatch('/opt/hermes-runtime/programs/proof-java-[a-f0-9]{32}',str(java))
            and re.fullmatch('/run/ec-rea-program-proof-[a-f0-9]{32}',str(home))):
        raise ValueError('program_probe_binding_refused')
    fields=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines())
    if not (fields['NoNewPrivs'].strip()=='1' and all(fields[k].strip()=='0000000000000000' for k in ('CapEff','CapAmb','CapInh'))):
        raise ValueError('program_probe_privilege_refused')
    os.umask(0o077)
    env=runtime_environment(java,home)
    result=dict(complete=False,java_version_verified=False,ghidra_headless_import_passed=False,
        real_profiles_read=False,rea_server_started=False,model_called=False,external_sends=0)
    try:
        version=subprocess.run([str(java/'bin/java'),'-version'],env=env,cwd=home,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
        if version.returncode!=0 or b'21.0.13' not in version.stdout+version.stderr:raise ValueError('java_probe_failed')
        result['java_version_verified']=True
        project=home/'invented-projects';project.mkdir(mode=0o700)
        with open(os.devnull,'wb') as quiet:
            run=subprocess.run([str(ghidra/'support/analyzeHeadless'),str(project),'InventedReaDependencyQualification',
                '-import','/usr/bin/true','-noanalysis'],env=env,cwd=home,stdout=quiet,stderr=quiet,timeout=180)
        if run.returncode!=0 or not list(project.iterdir()):raise ValueError('ghidra_probe_failed')
        result.update(complete=True,ghidra_headless_import_passed=True)
    except Exception as error:
        result['error_kind']=type(error).__name__ if type(error).__name__ in {'ValueError','TimeoutExpired','OSError','PermissionError'} else 'other'
    with (home/'receipt.json').open('x') as out:json.dump(result,out,sort_keys=True);out.flush();os.fsync(out.fileno())
    return 0 if result['complete'] else 1


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:
        print('{"complete":false,"category":"rea_program_probe_refused"}')
        raise SystemExit(1)
