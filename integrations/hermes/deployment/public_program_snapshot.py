"""Bounded public REA dependency snapshots, never private profiles or projects.

An ordinary owner captures installed distribution bytes. A protected operator
validates the entire archive before writing a NEW public program directory.
No archive member is executed; no arbitrary tar extraction is used. This binds
installed bytes, not an independent claim about upstream release authenticity.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import tarfile
import time

MAX_BYTES = 1200 * 1024**2
MAX_ARCHIVE = MAX_BYTES + 32 * 1024**2
MAX_ENTRIES = 12000
MANIFEST = 'public-program-manifest.json'
TOP = {
    'ghidra': {'Extensions','GPL','GettingStarted.html','GettingStarted.md','Ghidra',
               'LICENSE','bom.json','docker','docs','ghidraRun','ghidraRun.bat','licenses','server','support'},
    'java': {'NOTICE','bin','conf','include','jmods','legal','lib','man','release'},
}
WINDOWS_WRITABLE = {
    'GPL/DemanglerGnu/os/win_x86_64/demangler_gnu_v2_41.exe',
    'GPL/DemanglerGnu/os/win_x86_64/demangler_gnu_v2_24.exe',
    'Ghidra/Features/FileFormats/os/win_x86_64/lzfse.exe',
    'Ghidra/Features/PDB/os/win_x86_64/pdb.exe',
    'Ghidra/Features/Decompiler/os/win_x86_64/decompile.exe',
    'Ghidra/Features/Decompiler/os/win_x86_64/sleigh.exe',
}


def require(value):
    if not value:
        raise ValueError('public_program_snapshot_refused')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def relative(name):
    require(isinstance(name,str) and 0 < len(name) <= 255 and name.isascii()
            and all(ord(c) >= 32 and ord(c) != 127 for c in name)
            and not name.startswith('/') and '\\' not in name
            and all(p not in {'','.','..'} for p in name.split('/')))
    for part in name.split('/'):
        lower=part.lower()
        require(not ('lswa' in lower or 'legal-social-frameworks' in lower)
                and lower not in {'.git','.env','auth.json','credentials.json','id_rsa','id_ed25519'}
                and not lower.endswith(('.gpr','.rep','.pem','.key')))
    return name


def stamp(info):
    return tuple(getattr(info,k) for k in ('st_dev','st_ino','st_uid','st_gid','st_mode',
                                         'st_nlink','st_size','st_mtime_ns','st_ctime_ns'))


def opened(root, name, *, directory=False):
    relative(name)
    fd=os.dup(root)
    try:
        parts=name.split('/')
        for index,part in enumerate(parts):
            flags=os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK
            if directory or index<len(parts)-1:flags|=os.O_DIRECTORY
            child=os.open(part,flags,dir_fd=fd);os.close(fd);fd=child
        return fd
    except BaseException:
        os.close(fd)
        raise


def source_root(path, *, owner_source=False):
    # Existing ~/tools is owner-owned 0775. Only unprivileged source capture
    # may cross that group-writable owner directory; protected destinations
    # retain strict ancestor permissions. No ancestor link is ever followed.
    require(type(owner_source) is bool)
    require(path.is_absolute() and '..' not in path.parts)
    fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            require('lswa' not in part.lower() and 'legal-social-frameworks' not in part.lower())
            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=child
            info=os.fstat(fd)
            require(info.st_uid in {0,os.geteuid()} and (not info.st_mode&0o022
                or owner_source and os.geteuid()>0 and info.st_uid==os.geteuid() and not info.st_mode&0o7002
                or info.st_uid==0 and info.st_mode&stat.S_ISVTX))
        return fd
    except BaseException:
        os.close(fd);raise


def distribution(program, entries, reader):
    """Check exact installed versions without running Java, Ghidra or REA."""
    if program=='ghidra':
        name='Ghidra/application.properties'
        require(name in entries)
        values={}
        for line in reader(name).decode().splitlines():
            if '=' in line:
                key,value=line.split('=',1);values[key.strip()]=value.strip()
        require(values.get('application.name')=='Ghidra' and values.get('application.version')=='12.1.4'
                and values.get('application.release.name')=='PUBLIC' and values.get('application.java.min')=='21')
        return dict(name='Ghidra',version='12.1.4',minimum_java='21')
    require(program=='java' and 'release' in entries)
    values={}
    for line in reader('release').decode().splitlines():
        if '=' in line:
            key,value=line.split('=',1);values[key]=value.strip('"')
    require(values.get('JAVA_VERSION')=='21.0.13' and values.get('IMPLEMENTOR')=='Eclipse Adoptium')
    return dict(name='Eclipse Adoptium',version='21.0.13')


def validate_links(entries):
    """Every link resolves lexically to an existing member within this bundle."""
    def normalize(parts):
        output=[]
        for p in parts:
            if p in {'','.'}:continue
            if p=='..':require(bool(output));output.pop()
            else:output.append(p)
        return output
    for name,row in entries.items():
        parts=name.split('/')
        for i in range(1,len(parts)):
            require(entries.get('/'.join(parts[:i]),{}).get('kind')=='directory')
        if row['kind']!='symlink':continue
        target=row['target']
        require(isinstance(target,str) and target.isascii() and 0<len(target)<=255
                and not target.startswith('/') and '\\' not in target)
        pending=normalize(parts[:-1]+target.split('/'))
        for _ in range(32):
            changed=False
            for index in range(1,len(pending)+1):
                link=entries.get('/'.join(pending[:index]))
                require(link is not None)
                if link['kind']=='symlink':
                    pending=normalize(pending[:index-1]+link['target'].split('/')+pending[index:])
                    changed=True;break
                require(index==len(pending) or link['kind']=='directory')
            if not changed:break
        else:require(False)
        require(bool(pending) and '/'.join(pending) in entries)


def capture(path, program):
    require(os.geteuid()>0 and program in TOP and isinstance(path,Path) and path.is_absolute())
    root=source_root(path,owner_source=True)
    deadline=time.monotonic()+180
    saved={};entries={};directories={};total=0
    try:
        require(os.fstat(root).st_uid==os.geteuid() and not os.fstat(root).st_mode&0o022)
        def walk(fd,prefix='',depth=0):
            require(depth<=24 and time.monotonic()<deadline)
            names=sorted(os.listdir(fd));directories[prefix]=(stamp(os.fstat(fd)),names)
            for name in names:
                full=relative(prefix+'/'+name if prefix else name)
                require(len(entries)<MAX_ENTRIES and full!=MANIFEST and full.split('/')[0] in TOP[program])
                info=os.stat(name,dir_fd=fd,follow_symlinks=False)
                require(info.st_uid==os.geteuid() and info.st_dev==os.fstat(root).st_dev)
                saved[full]=stamp(info)
                if stat.S_ISLNK(info.st_mode):
                    require(info.st_nlink==1)
                    entries[full]=dict(kind='symlink',target=os.readlink(name,dir_fd=fd),mode=0o777)
                else:
                    require(not info.st_mode&0o7002 or program=='ghidra' and full in WINDOWS_WRITABLE
                            and stat.S_IMODE(info.st_mode)==0o666)
                    if stat.S_ISDIR(info.st_mode):
                        entries[full]=dict(kind='directory',mode=0o755)
                        child=opened(root,full,directory=True)
                        try:require(stamp(os.fstat(child))==saved[full]);walk(child,full,depth+1)
                        finally:os.close(child)
                    else:
                        require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_size<=512*1024**2)
                        entries[full]=dict(kind='file',mode=0o755 if info.st_mode&stat.S_IXUSR else 0o644,size=info.st_size)
        walk(root);validate_links(entries)
        def read(name):
            fd=opened(root,name)
            with os.fdopen(fd,'rb') as f:
                require(stamp(os.fstat(f.fileno()))==saved[name]);raw=f.read(262145)
                require(len(raw)<=262144 and stamp(os.fstat(f.fileno()))==saved[name]);return raw
        metadata=distribution(program,entries,read)
        payload=io.BytesIO()
        with tarfile.open(fileobj=payload,mode='w',format=tarfile.GNU_FORMAT) as archive:
            for name,row in sorted(entries.items()):
                require(time.monotonic()<deadline)
                member=tarfile.TarInfo(name);member.mode=row['mode'];member.uid=member.gid=0
                if row['kind']=='directory':member.type=tarfile.DIRTYPE;archive.addfile(member)
                elif row['kind']=='symlink':member.type=tarfile.SYMTYPE;member.linkname=row['target'];archive.addfile(member)
                else:
                    total+=row['size'];require(total<=MAX_BYTES)
                    fd=opened(root,name)
                    with os.fdopen(fd,'rb') as stream:
                        require(stamp(os.fstat(stream.fileno()))==saved[name])
                        raw=stream.read(row['size']+1)
                        require(len(raw)==row['size'] and stamp(os.fstat(stream.fileno()))==saved[name])
                    row['sha256']=hashlib.sha256(raw).hexdigest();member.size=len(raw)
                    archive.addfile(member,io.BytesIO(raw))
            for name,before in saved.items():
                parts=PurePosixPath(name);parent=opened(root,str(parts.parent),directory=True) if str(parts.parent)!='.' else os.dup(root)
                try:require(stamp(os.stat(parts.name,dir_fd=parent,follow_symlinks=False))==before)
                finally:os.close(parent)
            for name,(before,names) in directories.items():
                fd=opened(root,name,directory=True) if name else os.dup(root)
                try:require(stamp(os.fstat(fd))==before and sorted(os.listdir(fd))==names)
                finally:os.close(fd)
            manifest=dict(format='hermes-public-program-v1',program=program,metadata=metadata,entries=entries,total_bytes=total)
            raw=canonical(manifest);require(len(raw)<=8*1024**2)
            member=tarfile.TarInfo(MANIFEST);member.mode=0o644;member.size=len(raw);archive.addfile(member,io.BytesIO(raw))
        body=payload.getvalue();require(len(body)<=MAX_ARCHIVE)
        return body,dict(program=program,files=sum(x['kind']=='file' for x in entries.values()),
            links=sum(x['kind']=='symlink' for x in entries.values()),source_bytes=total,
            archive_sha256=hashlib.sha256(body).hexdigest(),source_preserved=True,metadata=metadata)
    finally:os.close(root)


def validate(payload, program):
    require(program in TOP and isinstance(payload,bytes) and 0<len(payload)<=MAX_ARCHIVE)
    with tarfile.open(fileobj=io.BytesIO(payload),mode='r:') as archive:
        members={};total=0
        for member in archive:
            name=relative(member.name)
            require(name not in members and len(members)<=MAX_ENTRIES and not member.pax_headers
                and member.sparse is None and member.uid==member.gid==0
                and (member.isfile() or member.isdir() or member.issym()))
            require(member.mode in ({0o777} if member.issym() else {0o644,0o755})
                    and (member.isfile() or member.size==0))
            if member.isfile():total+=member.size;require(0<=member.size<=MAX_BYTES and total<=MAX_BYTES+8*1024**2)
            members[name]=member
        require(MANIFEST in members and members[MANIFEST].isfile() and members[MANIFEST].size<=8*1024**2)
        raw=archive.extractfile(members.pop(MANIFEST)).read(8*1024**2+1)
        manifest=json.loads(raw)
        require(canonical(manifest)==raw and set(manifest)=={'format','program','metadata','entries','total_bytes'}
            and manifest['format']=='hermes-public-program-v1' and manifest['program']==program
            and isinstance(manifest['entries'],dict) and set(manifest['entries'])==set(members))
        entries=manifest['entries'];used=0
        for name,row in entries.items():
            require(name.split('/')[0] in TOP[program] and isinstance(row,dict))
            member=members[name];kind=row.get('kind')
            require(row.get('mode')==member.mode)
            if kind=='directory':require(set(row)=={'kind','mode'} and member.isdir())
            elif kind=='symlink':require(set(row)=={'kind','mode','target'} and member.issym() and row['target']==member.linkname)
            else:
                require(kind=='file' and set(row)=={'kind','mode','size','sha256'} and member.isfile()
                    and type(row['size']) is int and row['size']==member.size)
                data=archive.extractfile(member).read(member.size+1)
                require(len(data)==member.size and hashlib.sha256(data).hexdigest()==row['sha256']);used+=len(data)
        require(type(manifest['total_bytes']) is int and used==manifest['total_bytes']<=MAX_BYTES)
        validate_links(entries)
        require(distribution(program,entries,lambda name: archive.extractfile(members[name]).read(262145))==manifest['metadata'])
        return manifest


def restore(payload, program, destination):
    """The operator supplies a NEW fixed destination; validation precedes writes."""
    manifest=validate(payload,program)
    require(isinstance(destination,Path) and destination.is_absolute() and '..' not in destination.parts
            and not os.path.lexists(destination))
    for parent in reversed(destination.parents):
        info=parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid in {0,os.geteuid()}
            and (not info.st_mode&0o022 or info.st_uid==0 and info.st_mode&stat.S_ISVTX))
    destination.mkdir(mode=0o755)
    root=os.open(destination,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        os.fchmod(root,0o755)
        with tarfile.open(fileobj=io.BytesIO(payload),mode='r:') as archive:
            for name,row in sorted(manifest['entries'].items(),key=lambda x:(len(x[0].split('/')),x[0])):
                if row['kind']=='symlink':continue
                path=PurePosixPath(name);parent=opened(root,str(path.parent),directory=True) if str(path.parent)!='.' else os.dup(root)
                try:
                    if row['kind']=='directory':
                        os.mkdir(path.name,0o755,dir_fd=parent)
                        child=os.open(path.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
                        try:os.fchmod(child,0o755)
                        finally:os.close(child)
                    else:
                        fd=os.open(path.name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=parent)
                        with os.fdopen(fd,'wb') as output:
                            data=archive.extractfile(name).read(row['size']+1)
                            require(len(data)==row['size'] and hashlib.sha256(data).hexdigest()==row['sha256'])
                            output.write(data);output.flush();os.fchmod(output.fileno(),row['mode']);os.fsync(output.fileno())
                    os.fsync(parent)
                finally:os.close(parent)
            for name,row in manifest['entries'].items():
                if row['kind']=='symlink':
                    path=PurePosixPath(name);parent=opened(root,str(path.parent),directory=True) if str(path.parent)!='.' else os.dup(root)
                    try:os.symlink(row['target'],path.name,dir_fd=parent);os.fsync(parent)
                    finally:os.close(parent)
            fd=os.open(MANIFEST,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644,dir_fd=root)
            with os.fdopen(fd,'wb') as output:
                output.write(canonical(manifest));output.flush();os.fchmod(output.fileno(),0o644);os.fsync(output.fileno())
            os.fsync(root)
    finally:os.close(root)
    verify(destination,manifest)
    return manifest


def verify(destination,manifest):
    """Read back every restored byte/link/mode and reject extra directory entries."""
    root=source_root(destination)
    try:
        entries=manifest['entries'];children={'':{MANIFEST}}
        for name,row in entries.items():
            path=PurePosixPath(name);parent=str(path.parent)
            children.setdefault('' if parent=='.' else parent,set()).add(path.name)
            if row['kind']=='directory':children.setdefault(name,set())
        for name,expected in children.items():
            fd=opened(root,name,directory=True) if name else os.dup(root)
            try:
                info=os.fstat(fd)
                require(info.st_uid==os.geteuid() and stat.S_IMODE(info.st_mode)==0o755 and set(os.listdir(fd))==expected)
            finally:os.close(fd)
        for name,row in entries.items():
            if row['kind']=='directory':continue
            path=PurePosixPath(name);parent=opened(root,str(path.parent),directory=True) if str(path.parent)!='.' else os.dup(root)
            try:
                info=os.stat(path.name,dir_fd=parent,follow_symlinks=False)
                require(info.st_uid==os.geteuid() and info.st_nlink==1)
                if row['kind']=='symlink':require(stat.S_ISLNK(info.st_mode) and os.readlink(path.name,dir_fd=parent)==row['target'])
                else:
                    require(stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode)==row['mode'] and info.st_size==row['size'])
                    fd=opened(root,name);digest=hashlib.sha256();used=0
                    with os.fdopen(fd,'rb') as stream:
                        require(stamp(os.fstat(stream.fileno()))==stamp(info))
                        while data:=stream.read(1024**2):
                            used+=len(data);require(used<=row['size']);digest.update(data)
                        require(stamp(os.fstat(stream.fileno()))==stamp(info))
                    require(used==row['size'] and digest.hexdigest()==row['sha256'])
            finally:os.close(parent)
        fd=opened(root,MANIFEST)
        with os.fdopen(fd,'rb') as stream:require(stream.read(8*1024**2+1)==canonical(manifest))
    finally:os.close(root)
