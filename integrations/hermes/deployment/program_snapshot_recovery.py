"""Stream a reviewed immutable program tree; never traverse profile trees.

No secret mechanism, model call or service action lives in this core. The caller
must admit a fixed protected source and authenticated manifest. Extraction is
only into a new empty directory. Existing files are never overwritten.
"""
from __future__ import annotations
import hashlib
import io
import json
import os
from pathlib import Path,PurePosixPath
import stat
import tarfile

MANIFEST_LIMIT=16*1024*1024
FILE_LIMIT=512*1024*1024
TOTAL_LIMIT=3*1024**3
ENTRY_LIMIT=60000


class ProgramRecoveryError(ValueError):pass


def require(value):
    if not value:raise ProgramRecoveryError('program_snapshot_recovery_refused')


def parts(value):
    require(isinstance(value,str) and 0<len(value)<=2048 and '\x00' not in value and '\\' not in value)
    path=PurePosixPath(value)
    require(not path.is_absolute() and str(path)==value and all(p not in {'','.','..'}
        and 'lswa' not in p.lower() and 'legal-social-frameworks' not in p.lower() for p in path.parts))
    require(path.parts[0]!='operator-evidence')
    return path.parts


def validate_manifest(raw):
    require(isinstance(raw,bytes) and 0<len(raw)<=MANIFEST_LIMIT)
    value=json.loads(raw)
    require(isinstance(value,dict) and 0<len(value)<=ENTRY_LIMIT and 'snapshot-files.json' not in value)
    total=0
    for name,entry in value.items():
        path=parts(name);require(isinstance(entry,dict))
        require(not any('/'.join(path[:i]) in value for i in range(1,len(path))))
        if set(entry)=={'sha256','bytes'}:
            require(isinstance(entry['sha256'],str) and len(entry['sha256'])==64
                and all(c in '0123456789abcdef' for c in entry['sha256'])
                and type(entry['bytes']) is int and 0<=entry['bytes']<=FILE_LIMIT)
            total+=entry['bytes'];require(total<=TOTAL_LIMIT)
        else:
            require(set(entry)=={'link'});link_target(name,entry['link'])
    return value


def link_target(name,target):
    require(isinstance(target,str) and 0<len(target)<=2048 and '\x00' not in target and '\\' not in target
        and not PurePosixPath(target).is_absolute())
    result=list(parts(name)[:-1])
    for item in target.split('/'):
        if item in {'','.'}:continue
        if item=='..':require(result);result.pop()
        else:
            require('lswa' not in item.lower() and 'legal-social-frameworks' not in item.lower())
            result.append(item)
    require(result)
    return '/'.join(result)


def protected(info,uid,directory=False):
    require(info.st_uid==uid and not info.st_mode&0o6022
        and (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
        and (directory or info.st_nlink==1))


def directory(path,uid):
    require(path.is_absolute())
    fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            os.close(fd);fd=child
            # Tests can use an ordinary owner's private fixture beneath /tmp.
            # Production callers select only the fixed root-owned /opt tree.
            info=os.fstat(fd)
            require(info.st_uid in {0,uid} and (not info.st_mode&0o022 or part=='tmp' and info.st_mode&stat.S_ISVTX))
        protected(os.fstat(fd),uid,True)
        return fd
    except BaseException:os.close(fd);raise


def parent(root,path,uid,create=False):
    fd=os.dup(root)
    try:
        for part in path[:-1]:
            made=False
            if create:
                try:os.mkdir(part,0o755,dir_fd=fd);made=True
                except FileExistsError:pass
            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            os.close(fd);fd=child;protected(os.fstat(fd),uid,True)
            if made:os.fchmod(fd,0o755)
        return fd
    except BaseException:os.close(fd);raise


def stamp(info):
    return tuple(getattr(info,k) for k in ('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns'))


class HashingReader:
    def __init__(self,stream):self.stream=stream;self.hasher=hashlib.sha256();self.count=0
    def read(self,length):
        raw=self.stream.read(length);self.hasher.update(raw);self.count+=len(raw);return raw


def capture(source,raw,out,*,uid=0):
    manifest=validate_manifest(raw);root=directory(Path(source),uid);written=0
    try:
        # This streams through the caller's encryptor; no plaintext archive is
        # created. GNU long names are bounded and validated on restoration.
        with tarfile.open(fileobj=out,mode='w|',format=tarfile.GNU_FORMAT) as archive:
            header=tarfile.TarInfo('snapshot-files.json');header.size=len(raw);header.mode=0o644
            archive.addfile(header,io.BytesIO(raw))
            for name,entry in sorted(manifest.items(),key=lambda pair:('link' in pair[1],pair[0])):
                path=parts(name);base=parent(root,path,uid)
                try:
                    info=os.stat(path[-1],dir_fd=base,follow_symlinks=False)
                    header=tarfile.TarInfo(name)
                    if 'link' in entry:
                        require(stat.S_ISLNK(info.st_mode) and info.st_uid==uid and info.st_nlink==1
                            and os.readlink(path[-1],dir_fd=base)==entry['link'])
                        require(Path(source).joinpath(name).resolve(strict=True).is_relative_to(Path(source)))
                        header.type=tarfile.SYMTYPE;header.linkname=entry['link'];header.mode=0o777
                        archive.addfile(header)
                        require(stamp(os.stat(path[-1],dir_fd=base,follow_symlinks=False))==stamp(info))
                    else:
                        protected(info,uid);require(info.st_size==entry['bytes'])
                        fd=os.open(path[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=base)
                        with os.fdopen(fd,'rb') as stream:
                            require(stamp(os.fstat(stream.fileno()))==stamp(info))
                            reader=HashingReader(stream);header.size=info.st_size
                            header.mode=0o755 if info.st_mode&0o111 else 0o644
                            archive.addfile(header,reader)
                            require(reader.count==entry['bytes'] and reader.hasher.hexdigest()==entry['sha256']
                                and stamp(os.fstat(stream.fileno()))==stamp(info)
                                and stamp(os.stat(path[-1],dir_fd=base,follow_symlinks=False))==stamp(info))
                        written+=info.st_size
                finally:os.close(base)
        return dict(complete=True,files=sum('sha256' in v for v in manifest.values()),
            links=sum('link' in v for v in manifest.values()),bytes=written,manifest_sha256=hashlib.sha256(raw).hexdigest())
    finally:os.close(root)


def restore(stream,destination,expected_manifest_sha,*,uid=0):
    target=Path(destination)
    require(not os.path.lexists(target))
    # mkdir is exclusive. The caller chooses a fixed protected parent. No
    # existing program tree or running installation is selected for extraction.
    target.mkdir(mode=0o755)
    root=directory(target,uid);os.fchmod(root,0o755);seen=set();links=[];count=0
    try:
        with tarfile.open(fileobj=stream,mode='r|') as archive:
            header=archive.next()
            require(header is not None and header.name=='snapshot-files.json' and header.isreg()
                and not header.pax_headers and not header.sparse and 0<header.size<=MANIFEST_LIMIT)
            raw=archive.extractfile(header).read(MANIFEST_LIMIT+1)
            require(len(raw)==header.size and hashlib.sha256(raw).hexdigest()==expected_manifest_sha)
            manifest=validate_manifest(raw)
            fd=os.open('snapshot-files.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644,dir_fd=root)
            with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fchmod(out.fileno(),0o644);os.fsync(out.fileno())
            while (header:=archive.next()) is not None:
                name=header.name;path=parts(name)
                require(name in manifest and name not in seen and not header.pax_headers and not header.sparse)
                seen.add(name);entry=manifest[name]
                require(header.uid==header.gid==0 and not header.uname and not header.gname)
                if 'link' in entry:
                    require(header.issym() and header.size==0 and header.linkname==entry['link'])
                    link_target(name,header.linkname);links.append((path,header.linkname));continue
                require(header.isreg() and header.size==entry['bytes'] and header.mode in {0o644,0o755})
                base=parent(root,path,uid,True)
                try:
                    fd=os.open(path[-1],os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=base)
                    with os.fdopen(fd,'wb') as out:
                        incoming=HashingReader(archive.extractfile(header))
                        while chunk:=incoming.read(1024*1024):out.write(chunk)
                        require(incoming.count==entry['bytes'] and incoming.hasher.hexdigest()==entry['sha256'])
                        out.flush();os.fchmod(out.fileno(),header.mode);os.fsync(out.fileno())
                        count+=incoming.count
                finally:os.close(base)
            require(seen==set(manifest))
            for path,value in links:
                base=parent(root,path,uid,True)
                try:os.symlink(value,path[-1],dir_fd=base)
                finally:os.close(base)
            for path,value in links:
                require(target.joinpath(*path).resolve(strict=True).is_relative_to(target))
            os.fsync(root)
            return dict(complete=True,files=len(seen)-len(links),links=len(links),bytes=count,
                manifest_sha256=hashlib.sha256(raw).hexdigest(),source_tree_changed=False,
                program_executed=False,fresh_machine_source_build_qualified=False)
    finally:os.close(root)
