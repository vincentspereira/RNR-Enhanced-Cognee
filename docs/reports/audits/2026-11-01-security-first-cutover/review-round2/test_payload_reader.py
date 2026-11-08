"""Execute ONLY the ordinary-user payload-reader block, never sudo/root code."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest

OUT = Path(__file__).resolve().parent
PIN = 'd9424c108646f4a88a9cb8babad92d7335497b194d9fc80e6b27452e91731f63'


@pytest.mark.parametrize('variant', ['exact', 'mismatch', 'symlink', 'absent'])
def test_B05_real_ordinary_payload_reader(variant, tmp_path):
    assert os.geteuid() != 0
    payload = tmp_path / 'payload.py'
    data = b'# explicitly invented non-executable payload bytes\n'
    payload.write_bytes(data)
    requested = payload
    if variant == 'symlink':
        requested = tmp_path / 'alias.py'
        requested.symlink_to(payload)
    elif variant == 'absent':
        requested = tmp_path / 'absent.py'
    expected = '0' * 64 if variant == 'mismatch' else hashlib.sha256(data).hexdigest()
    code = (OUT / 'owner-python-2.py').read_text('ascii')
    result = subprocess.run(['/usr/bin/python3', '-I', '-S', '-B', '-c', code, str(requested), expected],
                            cwd=tmp_path, env={'PATH': '/usr/bin:/bin'}, capture_output=True, timeout=10)
    (tmp_path / 'process-receipt.json').open('x').write(json.dumps(dict(variant=variant, returncode=result.returncode,
        stdout_sha256=hashlib.sha256(result.stdout).hexdigest(), stdout_bytes=len(result.stdout), stderr=result.stderr.decode('ascii')), indent=2) + '\n')
    if variant == 'exact':
        assert result.returncode == 0 and result.stdout == data and result.stderr == b''
    else:
        assert result.returncode != 0 and result.stdout == b''
    assert payload.read_bytes() == data
