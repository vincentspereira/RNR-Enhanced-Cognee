"""Invented REA program bundles: archive boundaries and byte-preserving recovery."""
import io
import json
import os
from pathlib import Path
import runpy
import tarfile

import pytest

FOLDER=Path(__file__).resolve().parents[2]/'integrations/hermes/deployment'
H=runpy.run_path(str(FOLDER/'public_program_snapshot.py'))


def java(root):
    root.mkdir(mode=0o755)
    (root/'bin').mkdir();(root/'lib').mkdir();(root/'legal').mkdir()
    (root/'release').write_text('JAVA_VERSION="21.0.13"\nIMPLEMENTOR="Eclipse Adoptium"\n')
    (root/'bin/java').write_bytes(b'invented-program-not-executed');(root/'bin/java').chmod(0o755)
    (root/'lib/notices').write_bytes(b'invented-public-notice')
    (root/'legal/notice').symlink_to('../lib/notices')
    return root


def test_actual_archive_roundtrip_normalizes_only_destination_permissions(tmp_path):
    root=java(tmp_path/'source');before=(root/'bin/java').read_bytes()
    body,receipt=H['capture'](root,'java')
    old=os.umask(0o077)
    try:manifest=H['restore'](body,'java',tmp_path/'new-protected-copy')
    finally:os.umask(old)
    dest=tmp_path/'new-protected-copy'
    assert (dest/'bin/java').read_bytes()==before
    assert (dest/'legal/notice').read_bytes()==b'invented-public-notice'
    assert os.readlink(dest/'legal/notice')=='../lib/notices'
    assert all((dest/n).stat().st_mode&0o777==0o755 for n in ['bin','legal','bin/java'])
    assert (dest/'release').stat().st_mode&0o777==0o644
    assert receipt['files']==3 and receipt['links']==1 and receipt['source_preserved']
    assert manifest['program']=='java'
    assert (root/'bin/java').read_bytes()==before


@pytest.mark.parametrize('damage',['outside_link','cycle','hardlink','secret','project','unreviewed_top','mode','version'])
def test_source_refuses_non_distribution_or_unsafe_entries(tmp_path,damage):
    root=java(tmp_path/'source')
    if damage=='outside_link':(root/'lib/escape').symlink_to('/invented/private')
    if damage=='cycle':(root/'lib/a').symlink_to('b');(root/'lib/b').symlink_to('a')
    if damage=='hardlink':os.link(root/'lib/notices',root/'lib/alias')
    if damage=='secret':(root/'lib/.env').write_text('invented-non-secret')
    if damage=='project':(root/'lib/private.gpr').write_text('invented-project')
    if damage=='unreviewed_top':(root/'unreviewed').write_text('invented')
    if damage=='mode':(root/'bin/java').chmod(0o4777)
    if damage=='version':(root/'release').write_text('JAVA_VERSION="invented-other"\n')
    with pytest.raises(ValueError):H['capture'](root,'java')


@pytest.mark.parametrize('damage',['traversal','hardlink','payload','link','mode','unknown','duplicate','count'])
def test_hostile_archive_never_creates_a_destination(tmp_path,damage):
    body,_=H['capture'](java(tmp_path/'source'),'java');out=io.BytesIO()
    with tarfile.open(fileobj=io.BytesIO(body)) as source,tarfile.open(fileobj=out,mode='w',format=tarfile.GNU_FORMAT) as target:
        for member in source:
            raw=source.extractfile(member).read() if member.isfile() else None
            if member.name=='bin/java':
                if damage=='traversal':member.name='../outside'
                if damage=='payload':raw=b'changed'+raw;member.size=len(raw)
                if damage=='mode':member.mode=0o4755
                if damage=='hardlink':member.type=tarfile.LNKTYPE;member.linkname='release';member.size=0;raw=None
            if damage=='link' and member.issym():member.linkname='/invented/private'
            if member.name==H['MANIFEST'] and damage=='count':
                value=json.loads(raw);value['total_bytes']+=1;raw=H['canonical'](value);member.size=len(raw)
            target.addfile(member,io.BytesIO(raw) if raw is not None else None)
            if damage=='duplicate' and member.name=='release':target.addfile(member,io.BytesIO(raw))
        if damage=='unknown':
            member=tarfile.TarInfo('lib/unknown');member.mode=0o644;target.addfile(member,io.BytesIO(b''))
    dest=tmp_path/'must-not-exist'
    with pytest.raises(ValueError):H['restore'](out.getvalue(),'java',dest)
    assert not dest.exists()


def test_existing_directory_is_preserved(tmp_path):
    body,_=H['capture'](java(tmp_path/'source'),'java')
    dest=tmp_path/'existing';dest.mkdir();(dest/'retained').write_text('invented')
    with pytest.raises(ValueError):H['restore'](body,'java',dest)
    assert (dest/'retained').read_text()=='invented'


def test_root_cannot_walk_owner_programs(monkeypatch,tmp_path):
    monkeypatch.setattr(os,'geteuid',lambda:0)
    with pytest.raises(ValueError):H['capture'](tmp_path,'java')


@pytest.mark.parametrize('damage',['bytes','mode','extra','manifest'])
def test_readback_refuses_changed_restored_files_or_metadata(tmp_path,damage):
    body,_=H['capture'](java(tmp_path/'source'),'java');dest=tmp_path/'restored'
    manifest=H['restore'](body,'java',dest)
    if damage=='bytes':(dest/'bin/java').write_bytes(b'changed-public-binary')
    if damage=='mode':(dest/'bin/java').chmod(0o777)
    if damage=='extra':(dest/'lib/unexpected').write_bytes(b'invented')
    if damage=='manifest':(dest/H['MANIFEST']).write_bytes(b'{}')
    with pytest.raises(ValueError):H['verify'](dest,manifest)


def test_source_ancestor_link_is_not_followed(tmp_path):
    actual=java(tmp_path/'actual');(tmp_path/'redirect').symlink_to(tmp_path,target_is_directory=True)
    with pytest.raises(OSError):H['capture'](tmp_path/'redirect/actual','java')
