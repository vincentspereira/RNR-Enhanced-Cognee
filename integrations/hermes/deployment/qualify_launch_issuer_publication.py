"""Finite manual/scheduled publication components; never enable fleet policy.

Uses protected v2 issuer children on NEW invented scopes. The separate one-shot
timer qualifies only this component job, not fleet scheduling or gateway reload.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import subprocess
import sys
import time
import uuid

BASE = Path("/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529")
PACKAGE = BASE / "operator-issuer-candidate-v2"
ARTIFACT = BASE / "operator-issuer-publication-probe"
EVIDENCE = BASE / "operator-evidence/issuer-publication-v2"
FIXTURES = Path("/var/lib/hermes-renewal-qualification")
PINS = {"renew_fleet_credentials.py":"a7432a8a6c258b2f81466f51b782dd9b53c2211a5a52fcb863f3a1567ad858bf",
        "qualify_launch_issuer_reconciliation.py":"93977838f5c73e385656a36ee5a54fc011ee5de39937f0f83eb9bd9334ffec95",
        "recover_launch_graph_operator.py":"d7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef"}


def require(value,reason):
    if not value:raise ValueError(reason)


def definitions(path,expected):
    raw = path.read_bytes()
    require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == expected,"reviewed_source_required")
    result = {"__name__":"verified_publication_probe","__file__":str(path)}
    exec(compile(raw,"<verified-publication-probe>","exec"),result)
    return result


def fixture_entry(ident,account,policy):
    require(isinstance(ident,str) and re.fullmatch(r"[a-f0-9]{16}",ident),"fixed_fixture_identifier_required")
    return dict(name="pub_"+ident,user=account.pw_name,uid=account.pw_uid,home=account.pw_dir,
        profile=str(FIXTURES / ("issuer_"+ident)),tenant="qualification",project_id="pub_"+ident,
        subject="pub_"+ident,agent_id="issuer_publication",roles=["api_client"],lifetime_seconds=86400,
        origin=policy["ORIGIN"],executable=policy["EXECUTABLE"],enabled=False,reload_qualified=False,
        launch_binding_qualified=False,backup_qualified=False,os_boundary_qualified=False)


def publish_case(ident,driver,setup,core,policy,write):
    account = pwd.getpwnam("hermes-runtime")
    entry = fixture_entry(ident,account,policy)
    case = EVIDENCE / ident
    case.mkdir(mode=0o700)
    result = dict(complete=False,fixture_id=ident,checkpoint="new_fixture",memory_records_written=False,
                  model_called=False,existing_profiles_changed=False,qualification_credentials_issued=0)
    invocation = os.environ.get("INVOCATION_ID","")
    if re.fullmatch(r"[a-f0-9]{32}",invocation):result["unit_invocation_id"] = invocation
    write(case / "started.json",json.dumps(result).encode())
    try:
        profile = Path(entry["profile"])
        # The retained root/owner recovery helper uses this exact protected
        # parent. Root creates/chowns only a new empty directory, never walks it.
        driver["protected"](FIXTURES)
        profile.mkdir(mode=0o700)
        os.chown(profile,account.pw_uid,account.pw_gid)
        identity = dict(sub=entry["subject"],agent_id=entry["agent_id"],tenant=entry["tenant"],project_id=entry["project_id"],
                        roles=["api_client"],capture_policy="selected")
        core["IDENTITY"] = identity
        key = core["load_signing_key"]()
        now = int(time.time())
        old = core["sign_claims"](dict(identity,iat=now-72000,exp=now+14400),key)
        bundle = core["make_bundle"](key,now)
        del key
        result["qualification_credentials_issued"] = 2
        ledger = case / "root-ledger"
        ledger.mkdir(mode=0o700)
        driver["LEDGER"] = ledger
        root_id = entry["name"]+"-"+uuid.uuid4().hex
        directory = core["open_directory"](ledger,{0})
        try:
            driver["ledger_write"](directory,root_id+".started.json",dict(profile=entry["name"],state="started",source_hashes=driver["SOURCES"]))
            driver["ledger_write"](directory,root_id+".issued.json",dict(schema=1,profile=entry["name"],entry_sha256=driver["binding_digest"](entry),
                source_hashes=driver["SOURCES"],driver_sha256=PINS["renew_fleet_credentials.py"],issued_token_sha256=hashlib.sha256(bundle["token"].encode()).hexdigest()))
        finally:os.close(directory)
        result["checkpoint"] = "prepare_new_owner_fixture"
        setup["initialize_fixture"](account,dict(id=ident,phase="prepared",entry=entry,old=old,bundle=bundle,driver_sha256=PINS["renew_fleet_credentials.py"]))
        result["checkpoint"] = "installed_publication_child"
        report = driver["run_child"](entry,bundle,driver["sources"]())
        require(report["credential_published"] is True and report["interrupted_attempts_reconciled"] == 1,"actual_publication_not_verified")
        directory = core["open_directory"](ledger,{0})
        try:driver["ledger_write"](directory,root_id+".done.json",report)
        finally:os.close(directory)
        require(driver["attempt_closed"](core,entry,ledger / (root_id+".started.json")),"bound_completion_not_verified")
        result.update(complete=True,checkpoint="complete",installed_publication_component_qualified=True,
            refusal_controls_passed=True,previous_environment_settings_and_oauth_preserved=True,
            prepared_owner_journal_reconciled=True,bound_root_completion_verified=True,root_keys_withheld_from_children=True)
    except Exception as error:
        result["category"] = "publication_component_incomplete_preserve_evidence"
        allowed = {"actual_publication_not_verified","bound_completion_not_verified","fixture_interruption_failed_preserve_evidence",
                   "child_refused_review_retained_attempt","operator_resolution_binding_differs"}
        if type(error) is ValueError and str(error) in allowed:result["reason"] = str(error)
    write(case / "summary.json",json.dumps(result).encode())
    return result


def timer_command(ident):
    require(re.fullmatch(r"[a-f0-9]{16}",ident),"fixed_fixture_identifier_required")
    return ["/usr/bin/systemd-run","--quiet","--unit=ec-issuer-publication-"+ident,"--on-active=15s",
        "--timer-property=AccuracySec=1s","--property=Type=oneshot","--property=User=root","--property=Group=root",
        "--property=UMask=0077","--property=NoNewPrivileges=yes","--property=PrivateTmp=yes",
        "--property=ProtectHome=yes","--property=ProtectSystem=strict","--property=Restart=no",
        "--property=TimeoutStartSec=120","--property=LimitCORE=0",
        "--property=CapabilityBoundingSet=CAP_SETUID CAP_SETGID CAP_CHOWN",
        "--property=ReadWritePaths="+str(EVIDENCE)+" "+str(FIXTURES),
        str(BASE / "runtime/bin/python"),"-I","-B",str(ARTIFACT / "qualify_launch_issuer_publication.py"),"--scheduled",ident]


def unit_metadata(unit):
    process = subprocess.run(["/usr/bin/systemctl","show",unit,"--property=ActiveState,SubState,Result,ExecMainStatus,User,InvocationID,ExecMainStartTimestampMonotonic,LastTriggerUSecMonotonic"],
        stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=10,env={"PATH":"/usr/bin:/bin","LANG":"C.UTF-8"})
    require(process.returncode == 0 and len(process.stdout) <= 4096,"bounded_unit_metadata_required")
    return dict(line.split("=",1) for line in process.stdout.decode("ascii").splitlines() if "=" in line)


def scheduled_proof(case,service,timer):
    require(isinstance(case,dict) and case.get("complete") is True
        and re.fullmatch(r"[a-f0-9]{32}",case.get("unit_invocation_id",""))
        and service.get("ActiveState") == "inactive" and service.get("Result") == "success"
        and service.get("ExecMainStatus") == "0" and service.get("User") == "root"
        and int(service.get("ExecMainStartTimestampMonotonic","0")) > 0
        and service.get("InvocationID","") in {"",case["unit_invocation_id"]}
        and int(timer.get("LastTriggerUSecMonotonic","0")) > 0,"scheduled_publication_not_verified")


def main():
    require(os.geteuid() == 0,"fixed_root_operator_required")
    scheduled = len(sys.argv) == 3 and sys.argv[1] == "--scheduled"
    require(len(sys.argv) == 1 or scheduled,"fixed_probe_action_required")
    os.umask(0o077)
    support_path = ARTIFACT / "recover_launch_graph_operator.py" if scheduled else Path(__file__).with_name("recover_launch_graph_operator.py")
    support = definitions(support_path,PINS["recover_launch_graph_operator.py"])
    read,write = support["read_file"],support["private_write"]
    prior = json.loads(read(BASE / "operator-evidence/issuer-reconciliation-v2/summary.json",0))
    require(prior.get("complete") is True and prior.get("installed_issuer_reconciliation_qualified") is True,"completed_reconciliation_required")
    driver = definitions(PACKAGE / "renew_fleet_credentials.py",PINS["renew_fleet_credentials.py"])
    driver["protected"](PACKAGE / "renew_fleet_credentials.py")
    source = driver["sources"]()
    policy = driver["definitions"](source["fleet_credential_policy.py"],"publication_policy")
    original_policy = read(driver["POLICY"],0)
    require(not any(row["enabled"] for row in policy["load"](driver["POLICY"])["profiles"]),"fleet_must_remain_disabled")
    if not scheduled:
        EVIDENCE.mkdir(mode=0o700)
        ARTIFACT.mkdir(mode=0o755)
        ARTIFACT.chmod(0o755)
        for name,expected in PINS.items():
            if name == "renew_fleet_credentials.py":continue
            raw = Path(__file__).with_name(name).read_bytes()
            require(hashlib.sha256(raw).hexdigest() == expected,"reviewed_probe_support_required")
            write(ARTIFACT / name,raw)
            (ARTIFACT / name).chmod(0o644)
        write(ARTIFACT / Path(__file__).name,Path(__file__).read_bytes())
        (ARTIFACT / Path(__file__).name).chmod(0o644)
    require(Path(__file__).parent == ARTIFACT if scheduled else True,"protected_scheduled_source_required")
    driver["protected"](ARTIFACT / "qualify_launch_issuer_publication.py")
    setup = definitions(ARTIFACT / "qualify_launch_issuer_reconciliation.py",PINS["qualify_launch_issuer_reconciliation.py"])
    core = driver["definitions"](source["provision_pilot_access.py"],"publication_operator")
    if scheduled:
        ident = sys.argv[2]
        ticket = json.loads(read(EVIDENCE / "scheduled-ticket.json",0))
        require(ticket == dict(id=ident,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),"scheduled_ticket_binding_required")
        result = publish_case(ident,driver,setup,core,policy,write)
        require(read(driver["POLICY"],0) == original_policy,"fleet_policy_changed_concurrently")
        return 0 if result["complete"] else 1
    result = dict(complete=False,evidence=str(EVIDENCE),source_revision=BASE.name,checkpoint="manual_publication",
        fleet_launch_approved=False,installed_issuer_qualified=False,scheduled_firing_qualified=False,
        running_gateway_reload_qualified=False,policy_entry_admission_qualified=False,production_renewal_timer_enabled=False,
        existing_profiles_changed=False,keys_changed=False,memory_records_written=False,model_called=False)
    write(EVIDENCE / "started.json",json.dumps(result).encode())
    try:
        manual = publish_case(uuid.uuid4().hex[:16],driver,setup,core,policy,write)
        require(manual["complete"] is True,"manual_publication_failed")
        ident = uuid.uuid4().hex[:16]
        write(EVIDENCE / "scheduled-ticket.json",json.dumps(dict(id=ident,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())).encode())
        result["checkpoint"] = "one_shot_scheduled_publication"
        process = subprocess.run(timer_command(ident),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15,
            env={"PATH":"/usr/bin:/bin","LANG":"C.UTF-8"})
        require(process.returncode == 0,"one_shot_timer_creation_failed")
        result["transient_qualification_timer_created"] = True
        result["scheduled_unit"] = "ec-issuer-publication-"+ident+".service"
        deadline = time.monotonic()+150
        scheduled_result = None
        while time.monotonic() < deadline:
            try:
                scheduled_result = json.loads(read(EVIDENCE / ident / "summary.json",0))
            except FileNotFoundError:pass
            metadata = unit_metadata("ec-issuer-publication-"+ident+".service")
            if metadata.get("ActiveState") == "failed" or (scheduled_result is not None and metadata.get("ActiveState") == "inactive"):break
            time.sleep(1)
        else:raise ValueError("scheduled_publication_deadline")
        timer = unit_metadata("ec-issuer-publication-"+ident+".timer")
        scheduled_proof(scheduled_result,metadata,timer)
        require(read(driver["POLICY"],0) == original_policy,"fleet_policy_changed_concurrently")
        write(EVIDENCE / "scheduled-unit-metadata.json",json.dumps(dict(service=metadata,timer=timer)).encode())
        result.update(complete=True,checkpoint="complete",installed_publication_component_qualified=True,
            scheduled_publication_component_qualified=True,qualification_credentials_issued=4,new_synthetic_profile_count=2,
            unchanged_disabled_fleet_policy=True,scheduled_evidence=str(EVIDENCE / ident))
    except Exception as error:
        result["category"] = "issuer_publication_probe_incomplete_preserve_evidence"
        allowed = {"manual_publication_failed","one_shot_timer_creation_failed","scheduled_publication_deadline",
                   "scheduled_publication_not_verified","fleet_policy_changed_concurrently"}
        if type(error) is ValueError and str(error) in allowed:result["reason"] = str(error)
    write(EVIDENCE / "summary.json",json.dumps(result).encode())
    print(json.dumps(result))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    try:raise SystemExit(main())
    except Exception:
        print('{"complete":false,"category":"issuer_publication_preflight_refused_no_secret_output"}')
        raise SystemExit(1)
