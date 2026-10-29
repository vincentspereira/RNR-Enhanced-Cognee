"""Recover static program bytes, never existing paths or external link targets."""
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import subprocess
import shutil
import tarfile

import pytest

DIRECTORY=Path(__file__).resolve().parents[2]/'integrations/hermes/deployment'
CORE=runpy.run_path(str(DIRECTORY/'program_snapshot_recovery.py'),run_name='public_program_recovery_unit')
ERROR=CORE['ProgramRecoveryError']


def source(tmp_path):
    root=tmp_path/'program';root.mkdir(mode=0o755)
    (root/'bin').mkdir();(root/'bin/run').write_bytes(b'#!/bin/sh\nexit 0\n');(root/'bin/run').chmod(0o755)
    long='package_'+('a'*140)
    (root/long).mkdir();(root/long/'module.py').write_bytes(b'INVENTED = True\n')
    (root/'current').symlink_to(long,target_is_directory=True)
    value={p.relative_to(root).as_posix():({'link':os.readlink(p)} if p.is_symlink() else
        {'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        for p in root.rglob('*') if p.is_file() or p.is_symlink()}
    return root,json.dumps(value).encode()


def archive(root,raw):
    out=io.BytesIO();result=CORE['capture'](root,raw,out,uid=os.geteuid())
    return out.getvalue(),result


def test_streamed_roundtrip_preserves_bytes_exec_mode_and_internal_links(tmp_path):
    root,raw=source(tmp_path);packed,captured=archive(root,raw)
    target=tmp_path/'restored'
    result=CORE['restore'](io.BytesIO(packed),target,hashlib.sha256(raw).hexdigest(),uid=os.geteuid())
    assert captured['files']==result['files']==2 and captured['links']==result['links']==1
    assert (target/'bin/run').read_bytes()==(root/'bin/run').read_bytes()
    assert (target/'bin/run').stat().st_mode&0o777==0o755
    assert (target/'current').resolve().is_relative_to(target)
    assert result['program_executed'] is result['fresh_machine_source_build_qualified'] is False


@pytest.mark.parametrize('damage',['escape','absolute','directory_link_parent','privilege','hardlink','mismatch','extra_member'])
def test_untrusted_archive_members_fail_without_overwriting_original(tmp_path,damage):
    root,raw=source(tmp_path);packed,_=archive(root,raw)
    before=(root/'bin/run').read_bytes();new=io.BytesIO()
    with tarfile.open(fileobj=io.BytesIO(packed),mode='r:') as incoming,tarfile.open(fileobj=new,mode='w',format=tarfile.GNU_FORMAT) as outgoing:
        for member in incoming:
            data=incoming.extractfile(member).read() if member.isreg() else None
            if member.name=='bin/run':
                if damage=='escape':member.name='../original'
                elif damage=='absolute':member.name='/tmp/unrelated-original'
                elif damage=='directory_link_parent':member.name='current/other'
                elif damage=='privilege':member.mode=0o4755
                elif damage=='hardlink':member.type=tarfile.LNKTYPE;member.linkname='bin/run';member.size=0;data=None
                elif damage=='mismatch':data=b'X'*len(data)
            outgoing.addfile(member,io.BytesIO(data) if data is not None else None)
        if damage=='extra_member':outgoing.addfile(tarfile.TarInfo('unadmitted-extra'))
    with pytest.raises((ERROR,OSError)):
        CORE['restore'](io.BytesIO(new.getvalue()),tmp_path/'partial-preserved',hashlib.sha256(raw).hexdigest(),uid=os.geteuid())
    assert (root/'bin/run').read_bytes()==before


def test_existing_program_destination_is_never_opened_for_restoration(tmp_path):
    root,raw=source(tmp_path);packed,_=archive(root,raw)
    before=(root/'bin/run').read_bytes()
    with pytest.raises(ERROR):CORE['restore'](io.BytesIO(packed),root,hashlib.sha256(raw).hexdigest(),uid=os.geteuid())
    assert (root/'bin/run').read_bytes()==before


def test_source_file_hash_and_symlink_escape_fail_before_success(tmp_path):
    root,raw=source(tmp_path)
    (root/'bin/run').write_bytes(b'changed-source')
    with pytest.raises(ERROR):archive(root,raw)
    other=tmp_path/'outside';other.write_bytes(b'unrelated-never-read')
    value={'escape':{'link':'../outside'}}
    with pytest.raises(ERROR):CORE['validate_manifest'](json.dumps(value).encode())


@pytest.mark.parametrize('name',['../bad','/absolute','a/../bad','./bad','a//bad','operator-evidence/x','legal-social-frameworks/x'])
def test_manifest_rejects_unadmitted_paths(name):
    with pytest.raises(ERROR):CORE['validate_manifest'](json.dumps({name:{'bytes':0,'sha256':hashlib.sha256(b'').hexdigest()}}).encode())


def test_unauthenticated_manifest_never_creates_program_files(tmp_path):
    root,raw=source(tmp_path);packed,_=archive(root,raw)
    destination=tmp_path/'refused-restore'
    with pytest.raises(ERROR):CORE['restore'](io.BytesIO(packed),destination,'f'*64,uid=os.geteuid())
    assert list(destination.iterdir())==[]


def test_actual_age_binary_streams_invented_program_into_new_restoration(tmp_path):
    root,raw=source(tmp_path);identity=tmp_path/'invented-test-identity';encrypted=tmp_path/'invented-program.age'
    keygen=shutil.which('age-keygen');age=shutil.which('age')
    assert keygen and age, 'The real age and age-keygen binaries are required'
    subprocess.run([keygen,'--output',str(identity)],stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,check=True,timeout=10)
    recipient=subprocess.run([keygen,'-y',str(identity)],stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,check=True,timeout=10).stdout.decode().strip()
    with encrypted.open('xb') as out:
        process=subprocess.Popen([age,'--encrypt','--recipient',recipient],stdin=subprocess.PIPE,
            stdout=out,stderr=subprocess.DEVNULL)
        captured=CORE['capture'](root,raw,process.stdin,uid=os.geteuid());process.stdin.close()
        assert process.wait(timeout=10)==0
    with encrypted.open('rb') as incoming:
        process=subprocess.Popen([age,'--decrypt','--identity',str(identity)],stdin=incoming,
            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        restored=CORE['restore'](process.stdout,tmp_path/'age-restored-program',hashlib.sha256(raw).hexdigest(),uid=os.geteuid())
        while process.stdout.read(65536):pass
        assert process.wait(timeout=10)==0
    assert all(captured[k]==restored[k] for k in ('files','links','bytes','manifest_sha256'))
