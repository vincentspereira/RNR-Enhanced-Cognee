"""Stage v2 disabled issuer and qualify bound root/owner recovery components.

Two NEW disposable profiles use invented scopes and current ordinary tokens.
No existing profile, memory record, key, service or timer changes. This does not
admit synthetic paths into fleet policy or qualify running gateway renewal.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import pwd
import stat
import subprocess
import sys
import time
import uuid

BASE = Path("/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529")
PACKAGE = BASE / "operator-issuer-candidate-v2"
FIXTURES = Path("/var/lib/hermes-renewal-qualification")
STAGING_SHA256 = "2fcc1b6012eeb4dd2f606e14a8ad29ede1d97770cdbccb36e9e6c4ddea79f196"
SHARED_SHA256 = "d7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef"


def require(value,reason):
    if not value:raise ValueError(reason)


def definitions(path,expected):
    raw = path.read_bytes()
    require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == expected,"reviewed_source_required")
    namespace = {"__name__":"verified_issuer_recovery_probe","__file__":str(path)}
    exec(compile(raw,"<verified-issuer-recovery-probe>","exec"),namespace)
    return namespace


def setup_child(data):
    fields = dict(line.split(":",1) for line in Path("/proc/self/status").read_text().splitlines())
    uid = os.geteuid()
    require(uid == pwd.getpwnam("hermes-runtime").pw_uid and uid != 0 and not os.getgroups()
        and fields["NoNewPrivs"].strip() == "1" and all(fields[k].strip() == "0000000000000000" for k in ("CapEff","CapAmb")),
        "restricted_owner_required")
    entry = data["entry"]
    profile = Path(entry["profile"])
    require(profile.parent == FIXTURES and profile.name == "issuer_"+data["id"]
        and len(data["id"]) == 16 and all(c in "0123456789abcdef" for c in data["id"]),"fixed_new_fixture_required")
    driver = definitions(PACKAGE / "renew_fleet_credentials.py",data["driver_sha256"])
    source = driver["sources"]()
    core = driver["definitions"](source["provision_pilot_access.py"],"fixture_issuer")
    renewal = driver["definitions"](source["renew_pilot_access.py"],"fixture_journal")
    lifecycle = driver["definitions"](source["fleet_credential_lifecycle.py"],"fixture_transaction")
    core["IDENTITY"] = {"sub":entry["subject"],"agent_id":entry["agent_id"],"tenant":entry["tenant"],
                        "project_id":entry["project_id"],"roles":["api_client"],"capture_policy":"selected"}
    directory = core["open_directory"](profile,{0,uid})
    try:
        info = os.fstat(directory)
        require(info.st_uid == uid and stat.S_IMODE(info.st_mode) == 0o700,"private_fixture_required")
        files = {".env":("SYNTHETIC_UNRELATED=preserved\nENHANCED_COGNEE_ACCESS_TOKEN="+data["old"]+"\n").encode(),
            "config.yaml":b"memory:\n  provider: enhanced_cognee\n", "auth.json":b'{"synthetic_marker":"preserved"}',
            "enhanced_cognee.json":b'{"base_url":"http://127.0.0.1:28080","capture_policy":"selected","include_shared":true}'}
        for name,raw in files.items():core["create_private_at"](directory,name,raw)
        class Interrupted(Exception):pass
        def checkpoint(phase):
            if phase == data["phase"]:raise Interrupted()
        try:lifecycle["publish"](core,renewal,directory,data["bundle"],uid,checkpoint=checkpoint)
        except Interrupted:return {"complete":True,"requested_interruption_observed":True}
        raise ValueError("requested_interruption_not_observed")
    finally:os.close(directory)


def initialize_fixture(account,data):
    source = Path(__file__).read_bytes()
    require(len(source) <= 65536,"bounded_fixture_source_required")
    code = ("import json,sys\nn={'__name__':'owner_recovery_fixture'}\nexec(compile("+repr(source)+",'<owner-recovery-fixture>','exec'),n)\n"
        "try:\n print(json.dumps(n['setup_child'](json.load(sys.stdin))))\n"
        "except Exception:\n print('{\"complete\":false}');sys.exit(1)\n")
    raw = json.dumps(data).encode()
    require(len(raw) <= 16384,"bounded_fixture_input_required")
    process = subprocess.run(["/usr/bin/setpriv","--no-new-privs","--",data["entry"]["executable"],"-I","-B","-c",code],
        input=raw,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=60,cwd="/",user=account.pw_uid,group=account.pw_gid,
        extra_groups=(),env={"PATH":"/usr/bin:/bin","HOME":account.pw_dir,"LANG":"C.UTF-8","PYTHONDONTWRITEBYTECODE":"1"})
    require(process.returncode == 0 and len(process.stdout) <= 1024,"fixture_interruption_failed_preserve_evidence")
    require(json.loads(process.stdout) == {"complete":True,"requested_interruption_observed":True},"fixture_receipt_refused")


def main():
    require(os.geteuid() == 0 and len(sys.argv) == 1,"fixed_root_operator_required")
    os.umask(0o077)
    shared = definitions(Path(__file__).with_name("recover_launch_graph_operator.py"),SHARED_SHA256)
    read,write = shared["read_file"],shared["private_write"]
    custody = json.loads(read(Path("/var/lib/enhanced-cognee-rotation/candidate-gtnhc4kc/credential-custody-export/summary.json"),0))
    require(custody.get("complete") is True and custody.get("in_memory_decryption_verified") is True,"credential_export_required")
    stage = definitions(Path(__file__).with_name("stage_launch_issuer.py"),STAGING_SHA256)
    if not os.path.lexists(PACKAGE):
        previous = sys.argv
        try:
            sys.argv = ["stage_launch_issuer.py","--upgrade-disabled"]
            with contextlib.redirect_stdout(io.StringIO()):require(stage["main"]() == 0,"disabled_v2_staging_failed")
        finally:sys.argv = previous
    accepted = json.loads(read(BASE / "operator-evidence/issuer-preparation-v2/summary.json",0))
    require(accepted.get("complete") is True and accepted.get("existing_policy_preserved") is True,"disabled_v2_staging_required")
    driver = definitions(PACKAGE / "renew_fleet_credentials.py",stage["SOURCES"]["renew_fleet_credentials.py"])
    driver["protected"](PACKAGE / "renew_fleet_credentials.py")
    source = driver["sources"]()
    policy = driver["definitions"](source["fleet_credential_policy.py"],"fixture_policy")
    fleet = policy["load"](driver["POLICY"])
    require(not any(row["enabled"] for row in fleet["profiles"]),"fleet_must_remain_disabled")
    attempt = BASE / "operator-evidence/issuer-reconciliation-v2"
    attempt.mkdir(mode=0o700)
    ledger = attempt / "root-ledger"
    ledger.mkdir(mode=0o700)
    driver["LEDGER"] = ledger
    core = driver["definitions"](source["provision_pilot_access.py"],"root_recovery_fixture")
    account = pwd.getpwnam("hermes-runtime")
    info = FIXTURES.lstat()
    require(info.st_uid == 0 and stat.S_ISDIR(info.st_mode) and not info.st_mode & 0o022,"protected_fixture_parent_required")
    result = dict(complete=False,evidence=str(attempt),source_revision=BASE.name,existing_profiles_changed=False,
        keys_changed=False,services_changed=False,timer_enabled=False,memory_records_written=False,model_called=False,
        installed_issuer_qualified=False,scheduled_firing_qualified=False,running_gateway_reload_qualified=False,
        policy_entry_admission_qualified=False,fleet_launch_approved=False,qualification_credentials_issued=0,checkpoint="new_fixtures")
    write(attempt / "started.json",json.dumps(result).encode())
    try:
        reports = []
        for phase,outcome in (("prepared","not_published"),("published","published")):
            ident = uuid.uuid4().hex[:16]
            profile = FIXTURES / ("issuer_"+ident)
            profile.mkdir(mode=0o700)
            os.chown(profile,account.pw_uid,account.pw_gid)  # Newly created empty fixture only.
            entry = dict(name="issuer_"+ident,user=account.pw_name,uid=account.pw_uid,home=account.pw_dir,profile=str(profile),
                tenant="qualification",project_id="issuer_"+ident,subject="issuer_"+ident,agent_id="issuer_recovery",
                roles=["api_client"],lifetime_seconds=86400,origin=policy["ORIGIN"],executable=policy["EXECUTABLE"],
                enabled=False,reload_qualified=False,launch_binding_qualified=False,backup_qualified=False,os_boundary_qualified=False)
            identity = dict(sub=entry["subject"],agent_id=entry["agent_id"],tenant=entry["tenant"],project_id=entry["project_id"],
                roles=["api_client"],capture_policy="selected")
            core["IDENTITY"] = identity
            key = core["load_signing_key"]()
            now = int(time.time())
            old = core["sign_claims"](dict(identity,iat=now-72000,exp=now+14400),key)
            bundle = core["make_bundle"](key,now)
            del key
            result["qualification_credentials_issued"] += 2
            root_id = entry["name"]+"-"+uuid.uuid4().hex
            root_directory = core["open_directory"](ledger,{0})
            try:
                driver["ledger_write"](root_directory,root_id+".started.json",dict(profile=entry["name"],state="started",source_hashes=driver["SOURCES"]))
                driver["ledger_write"](root_directory,root_id+".issued.json",dict(schema=1,profile=entry["name"],
                    entry_sha256=driver["binding_digest"](entry),source_hashes=driver["SOURCES"],driver_sha256=stage["SOURCES"]["renew_fleet_credentials.py"],
                    issued_token_sha256=hashlib.sha256(bundle["token"].encode()).hexdigest()))
            finally:os.close(root_directory)
            result["checkpoint"] = "fixture_interruption_"+phase
            initialize_fixture(account,dict(id=ident,phase=phase,entry=entry,old=old,bundle=bundle,driver_sha256=stage["SOURCES"]["renew_fleet_credentials.py"]))
            result["checkpoint"] = "root_reconciliation_"+phase
            report = driver["reconcile_root"](core,entry,root_id,source)
            require(report["outcome"] == outcome and driver["attempt_closed"](core,entry,ledger / (root_id+".started.json")),"root_resolution_not_verified")
            try:driver["reconcile_root"](core,entry,root_id,source)
            except ValueError as error:require(str(error) == "operator_attempt_already_closed","duplicate_resolution_not_refused")
            else:raise ValueError("duplicate_resolution_not_refused")
            reports.append(dict(interruption=phase,outcome=outcome,environment_changed=False,duplicate_resolution_refused=True))
        require(policy["load"](driver["POLICY"]) == fleet,"fleet_policy_changed_concurrently")
        result.update(complete=True,checkpoint="complete",installed_issuer_reconciliation_qualified=True,interruption_outcomes=reports,
            existing_disabled_policy_preserved=True,new_synthetic_profile_count=2,root_keys_withheld_from_owner_children=True)
    except Exception as error:
        result["category"] = "issuer_reconciliation_qualification_incomplete_preserve_evidence"
        allowed = {"fixture_interruption_failed_preserve_evidence","fixture_receipt_refused","root_resolution_not_verified",
            "duplicate_resolution_not_refused","fleet_policy_changed_concurrently","issued_attempt_binding_requires_review",
            "issued_attempt_missing_or_ambiguous","child_refused_review_retained_attempt","operator_resolution_binding_differs"}
        if type(error) is ValueError and str(error) in allowed:result["reason"] = str(error)
        number = getattr(error,"errno",None)
        if type(number) is int and 0 < number < 4096:result["errno"] = number
    write(attempt / "summary.json",json.dumps(result).encode())
    print(json.dumps(result))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    try:raise SystemExit(main())
    except Exception:
        print('{"complete":false,"category":"issuer_reconciliation_preflight_refused_no_secret_output"}')
        raise SystemExit(1)
