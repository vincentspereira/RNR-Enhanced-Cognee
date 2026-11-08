"""Continue the stopped zero-effect pin refusal with an exact Node size bound."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

BASE=Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
PREVIOUS=BASE/'operator-main-rea-mcp-finish-v1'
PREVIOUS_SHA='483a4d97d8f6756d87047a0a7d1851db31c3dff77a94a1b8c076aa2ce412915e'
REFUSAL=BASE/'operator-evidence/main-local-mcp-rea-finish-evjjlpz3'
PREVIOUS_UNIT='ec-main-rea-mcp-finish-v1-20261028.service'
ARTIFACT=BASE/'operator-main-rea-mcp-finish-v2'
UNIT='ec-main-rea-mcp-finish-v2-20261028.service'
NODE=Path('/usr/bin/node')
NODE_SHA='41a74efb34cbde5c7632cdac0cf8bd1a14d0b8d73dc1e82755014d9a9ce70f5c'
NODE_BYTES=123655872
ATTRS=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')


def require(value):
    if not value:raise ValueError('rea_exact_node_continuation_refused')


def source():
    path=PREVIOUS/'finish_main_rea_mcp.py';raw=path.read_bytes()
    require(0<len(raw)<=65536 and hashlib.sha256(raw).hexdigest()==PREVIOUS_SHA)
    namespace={'__name__':'verified_retained_rea_finisher','__file__':str(path)}
    exec(compile(raw,'<verified-retained-rea-finisher>','exec'),namespace)
    return namespace


def node_shape(info):
    return (stat.S_ISREG(info.st_mode) and info.st_uid==0 and info.st_nlink==1
        and not info.st_mode&0o022 and info.st_size==NODE_BYTES)


def verified_node(path,digest):
    require(path==NODE and digest==NODE_SHA)
    for parent in reversed(path.parents):
        info=parent.lstat();require(stat.S_ISDIR(info.st_mode) and info.st_uid==0 and not info.st_mode&0o022)
    descriptor=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(descriptor,'rb') as stream:
        before=os.fstat(stream.fileno());require(node_shape(before))
        sha=hashlib.sha256();used=0
        while data:=stream.read(65536):
            used+=len(data);require(used<=NODE_BYTES);sha.update(data)
        after=os.fstat(stream.fileno());named=path.lstat()
        require(used==NODE_BYTES and sha.hexdigest()==NODE_SHA
            and all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in ATTRS))


def retained_refusal(namespace,old,read):
    context=json.loads(read(PREVIOUS/'context.private.json',0))
    require(context.get('source_sha256')==PREVIOUS_SHA and context.get('evidence')==str(REFUSAL)
        and isinstance(context.get('id'),str) and re.fullmatch('[a-f0-9]{32}',context['id'])
        and namespace['stopped'](old['metadata'](PREVIOUS_UNIT)))
    result=json.loads(read(REFUSAL/'finish.summary.json',0))
    require(result.get('source_revision')==BASE.name and result.get('operator_helper_sha256')==PREVIOUS_SHA
        and result.get('evidence')==str(REFUSAL) and result.get('complete') is False
        and result.get('checkpoint')=='public_code_pins' and result.get('error_kind')=='ValueError'
        and result.get('category')=='rea_catalogue_finish_incomplete_preserve_evidence'
        and all(type(result.get(k)) is int and result[k]==0 for k in
            ('credentials_issued','new_package_copies','external_platform_sends','platform_adapters_started'))
        and result.get('protected_public_programs_reused')==2
        and all(result.get(k) is True for k in ('operator_job_stopped','original_failure_preserved',
            'original_main_candidate_pass_preserved','all_admission_policies_preserved_disabled'))
        and all(result.get(k) is False for k in ('keys_read','model_called','memory_api_called','filesystem_replayed',
            'full_public_readback_replayed','java_ghidra_proof_replayed','source_profiles_changed','previous_candidates_changed',
            'main_tool_program_coverage_qualified','actual_profile_admission_qualified','production_dispatch_qualified',
            'production_renewal_timer_enabled','fleet_launch_approved')))
    # The failed operator never reached the proof-driver write or unit start.
    require(not os.path.lexists(old['PROGRAM_ROOT']/('mcp-driver-'+context['id']))
        and old['metadata']('ec-main-local-mcp-'+context['id']+'.service').get('LoadState')=='not-found'
        and not os.path.lexists(REFUSAL/'rea-component-receipt.json'))
    return result


def prepared():
    namespace=source();original_pin=namespace['public_pin'];original_retained=namespace['retained']
    def public_pin(path,digest):
        if path==NODE:return verified_node(path,digest)
        return original_pin(path,digest)
    def retained(old,read):
        retained_refusal(namespace,old,read)
        return original_retained(old,read)
    # Only a newly loaded namespace changes. The source/frozen V1 files and
    # its stopped failed result remain byte-for-byte unchanged.
    namespace.update(ARTIFACT=ARTIFACT,UNIT=UNIT,__file__=__file__,public_pin=public_pin,retained=retained)
    return namespace


def main():
    require(os.geteuid()==0 and sys.argv[1:] in ([],['--worker']))
    namespace=prepared()
    if not sys.argv[1:]:return namespace['launch']()
    old,_,read,_=namespace['helpers']();retained_refusal(namespace,old,read)
    saved={path:read(path,0) for path in (PREVIOUS/'context.private.json',PREVIOUS/'sources.json',
        REFUSAL/'summary.json',REFUSAL/'finish.summary.json')}
    try:return namespace['worker']()
    finally:require(all(read(path,0)==raw for path,raw in saved.items()))


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:
        print('{"complete":false,"category":"rea_exact_node_preflight_refused_no_secret_output"}',flush=True)
        raise SystemExit(1)
