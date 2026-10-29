"""Snapshot only the two existing public npm distributions, never profiles."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import pwd
import stat
import sys
import tempfile

BASE=Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
ARTIFACT=BASE/'operator-main-local-mcp-v1'
LIB_SHA='b180a6e83e9a00a7e287645adb3ea82db4455319029c44e2dc2d20e10087a42c'
LIB=ARTIFACT/'public_program_snapshot.py'
ARCHIVES=Path('/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/launch-worktree-20261024/.archive/2026-10-28-public-mcp-programs')
PACKAGES={
    'filesystem':dict(cache='a3241bba59c344f5',name='@modelcontextprotocol/server-filesystem',version='2026.8.31',entry='dist/index.js',
        archive_bytes=27525120,sha256='eeac2e4bd8302b1117c040fe251b3a565f740b28cb56011a727d756e7e7353de'),
    'rea':dict(cache='a1722018f28f9df2',name='rea-agents',version='6.7.0',entry='scripts/rea.mjs',
        archive_bytes=132792320,sha256='30a10da51b212810c6510497a87f6e93b15ea14da31702d38193a18d603ab623'),
}


def require(value):
    if not value:raise ValueError('public_mcp_bundle_refused')


def distribution(program,entries,reader):
    pin=PACKAGES[program];prefix='node_modules/'+pin['name']+'/'
    name=prefix+'package.json';require(name in entries and prefix+pin['entry'] in entries)
    data=reader(name);require(len(data)<=262144)
    value=json.loads(data)
    require(value.get('name')==pin['name'] and value.get('version')==pin['version']
        and entries[prefix+pin['entry']]['kind']=='file')
    return dict(name=pin['name'],version=pin['version'],entry=prefix+pin['entry'])


def library():
    raw=LIB.read_bytes();require(hashlib.sha256(raw).hexdigest()==LIB_SHA)
    scope={'__name__':'verified_public_mcp_archive','__file__':str(LIB)}
    exec(compile(raw,'<verified-public-mcp-archive>','exec'),scope)
    # A separate archive namespace, format and identities. Existing Java/Ghidra
    # code, artifacts and proof are unchanged and are never executed here.
    scope['TOP']={name:{'node_modules','package.json','package-lock.json'} for name in PACKAGES}
    scope['distribution']=distribution
    return scope


def stage_cache(program):
    """An ordinary owner copies public cache bytes into a NEW private tree.

    Existing npm cache directories are 0775. Their permissions are preserved;
    protected installation never traverses that cache. Stable descriptor reads,
    strict member names and complete directory/inode rechecks precede the
    existing strict private-tree archive capture and operator validation.
    """
    require(os.geteuid()>0 and program in PACKAGES)
    lib=library();source=Path('/home/vincentspereira/.npm/_npx')/PACKAGES[program]['cache']
    root=lib['source_root'](source,owner_source=True)
    target=Path(tempfile.mkdtemp(prefix='ec-public-mcp-',dir='/tmp'))
    observed=[];directories=[];total=0
    try:
        def walk(fd,destination,prefix='',depth=0):
            nonlocal total
            require(depth<=24 and len(observed)<lib['MAX_ENTRIES'])
            before=lib['stamp'](os.fstat(fd));names=sorted(os.listdir(fd));directories.append((prefix,before,names))
            for name in names:
                relative=lib['relative'](prefix+'/'+name if prefix else name)
                require(relative.split('/')[0] in lib['TOP'][program] and len(observed)<lib['MAX_ENTRIES'])
                info=os.stat(name,dir_fd=fd,follow_symlinks=False)
                require(info.st_uid==os.geteuid() and info.st_dev==os.fstat(root).st_dev
                    and (stat.S_ISLNK(info.st_mode) or not info.st_mode&0o7002))
                observed.append((relative,lib['stamp'](info)))
                destination_path=destination/name
                if stat.S_ISLNK(info.st_mode):
                    require(info.st_nlink==1);os.symlink(os.readlink(name,dir_fd=fd),destination_path)
                elif stat.S_ISDIR(info.st_mode):
                    destination_path.mkdir(mode=0o700)
                    child=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
                    try:require(lib['stamp'](os.fstat(child))==lib['stamp'](info));walk(child,destination_path,relative,depth+1)
                    finally:os.close(child)
                else:
                    require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_size<=512*1024**2)
                    total+=info.st_size;require(total<=lib['MAX_BYTES'])
                    opened=os.open(name,os.O_RDONLY|os.O_NONBLOCK|os.O_NOFOLLOW,dir_fd=fd)
                    with os.fdopen(opened,'rb') as stream:
                        require(lib['stamp'](os.fstat(stream.fileno()))==lib['stamp'](info))
                        raw=stream.read(info.st_size+1)
                        require(len(raw)==info.st_size and lib['stamp'](os.fstat(stream.fileno()))==lib['stamp'](info))
                    with destination_path.open('xb') as out:out.write(raw)
                    destination_path.chmod(0o755 if info.st_mode&stat.S_IXUSR else 0o600)
        walk(root,target)
        for name,before in observed:
            parent=Path(name).parent;fd=lib['opened'](root,str(parent),directory=True) if str(parent)!='.' else os.dup(root)
            try:require(lib['stamp'](os.stat(Path(name).name,dir_fd=fd,follow_symlinks=False))==before)
            finally:os.close(fd)
        for name,before,names in directories:
            fd=lib['opened'](root,name,directory=True) if name else os.dup(root)
            try:require(lib['stamp'](os.fstat(fd))==before and sorted(os.listdir(fd))==names)
            finally:os.close(fd)
        return target
    finally:os.close(root)


def child():
    packet=json.loads(sys.stdin.buffer.readline(8193));account=pwd.getpwuid(os.geteuid())
    fields=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines())
    require(set(packet)=={'mode','uid','gid','program'} and packet['mode']=='public_mcp_archive'
        and packet['program'] in PACKAGES and type(packet['uid']) is int and type(packet['gid']) is int
        and account.pw_name=='vincentspereira' and account.pw_dir=='/home/vincentspereira'
        and os.getresuid()==(packet['uid'],)*3 and os.getresgid()==(packet['gid'],)*3
        and account.pw_uid==packet['uid']>0 and account.pw_gid==packet['gid']>0 and not os.getgroups()
        and fields['NoNewPrivs'].strip()=='1'
        and all(fields[key].strip()=='0000000000000000' for key in ('CapEff','CapAmb','CapInh')))
    os.environ.clear();os.environ.update(PATH='/usr/bin:/bin',HOME=account.pw_dir,LANG='C.UTF-8')
    program=packet['program'];pin=PACKAGES[program]
    lib=library();directory=lib['source_root'](ARCHIVES,owner_source=True)
    try:
        fd=os.open(program+'.tar',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
        with os.fdopen(fd,'rb') as stream:
            before=os.fstat(stream.fileno())
            require(stat.S_ISREG(before.st_mode) and before.st_uid==os.geteuid() and before.st_nlink==1
                and stat.S_IMODE(before.st_mode)==0o600 and before.st_size==pin['archive_bytes'])
            body=stream.read(pin['archive_bytes']+1);after=os.fstat(stream.fileno())
            named=os.stat(program+'.tar',dir_fd=directory,follow_symlinks=False)
            require(len(body)==pin['archive_bytes'] and hashlib.sha256(body).hexdigest()==pin['sha256']
                and lib['stamp'](before)==lib['stamp'](after)==lib['stamp'](named))
    finally:os.close(directory)
    result=dict(complete=True,program=program,archive_bytes=len(body),archive_sha256=hashlib.sha256(body).hexdigest(),
        source_preserved=True)
    sys.stdout.buffer.write(json.dumps(result,sort_keys=True).encode()+b'\n'+body);sys.stdout.buffer.flush()
