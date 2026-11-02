"""Fresh shell pipeline control-flow probe; no sudo or protected operations."""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[6]
HELPER=ROOT/'integrations/hermes/deployment/prepare_security_first_cutover_v2.py'
OWNER=ROOT/'docs/reports/audits/2026-11-01-security-first-cutover/owner-plan-failure-20261102/repair-v2/OWNER-V2-PLAN.md'
assert hashlib.sha256(OWNER.read_bytes()).hexdigest()=='cbebb9eb0ae50451e5df431312ce9c7776dc90cabad1c5ec39ab2d3955bbeba0'


def test_owner_pipefail_retains_empty_target_and_stops(tmp_path):
    assert os.geteuid()!=0
    block=re.findall(r'```bash\n(.*?)```',OWNER.read_text(),re.S)[0]
    tokens=shlex.split(block.replace('\\\n',''))
    scripts=[tokens[i+1] for i,t in enumerate(tokens) if t=='-c']
    reader=scripts[1]
    # Replace only root installer dispatch with an unprivileged stdin sink.
    # The real /usr/bin/install and every sudo/root script are never executed.
    installer='import sys; data=sys.stdin.buffer.read(); open(sys.argv[1],"xb").write(data)'
    payload=tmp_path/'invented-source';payload.write_bytes(b'# INVENTED NONEXECUTED\n')
    for variant in ('positive','negative'):
        dest=tmp_path/variant;dest.mkdir(mode=0o700)
        installed=dest/'helper'; marker=dest/'next-step'
        expected=hashlib.sha256(payload.read_bytes()).hexdigest() if variant=='positive' else '0'*64
        script='set -euo pipefail\n'+shlex.join(['/usr/bin/python3','-I','-S','-B','-c',reader,str(payload),expected])+' | '+shlex.join(['/usr/bin/python3','-I','-S','-B','-c',installer,str(installed)])+'\n'+shlex.join(['/usr/bin/touch',str(marker)])+'\n'
        (dest/'double-pipeline.sh').write_text(script)
        result=subprocess.run(['/usr/bin/bash','-c',script],env={'PATH':'/usr/bin:/bin'},capture_output=True,timeout=10)
        (dest/'stdout.bin').write_bytes(result.stdout);(dest/'stderr.bin').write_bytes(result.stderr)
        (dest/'receipt.json').write_text(json.dumps({'variant':variant,'returncode':result.returncode,'installed_sha256':hashlib.sha256(installed.read_bytes()).hexdigest(),'installed_size':installed.stat().st_size,'next_step_ran':marker.exists()},indent=2)+'\n')
        assert result.stdout==b''
        if variant=='positive':
            assert result.returncode==0 and installed.read_bytes()==payload.read_bytes() and marker.exists()
        else:
            assert result.returncode!=0 and installed.exists() and installed.read_bytes()==b'' and not marker.exists()
            assert result.stderr==b'Source hash mismatch; no bytes emitted\n'
