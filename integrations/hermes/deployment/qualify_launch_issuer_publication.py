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
PUBLISHED_PROBE_SHA256 = "8e30a2bce14f694930edd8232f856c125e43bef2840bdea9f4864bef9cab7ea1"
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
    process = subprocess.run(["/usr/bin/systemctl","show",unit,"--property=LoadState,ActiveState,SubState,Result,ExecMainStatus,ExecMainCode,User,InvocationID,ExecMainStartTimestampMonotonic,LastTriggerUSecMonotonic,CapabilityBoundingSet,NoNewPrivileges,ProtectSystem,ProtectHome,ReadWritePaths"],
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


def safe_case_summary(value):
    allowed_phases = {"new_fixture","prepare_new_owner_fixture","installed_publication_child","complete"}
    result = {"complete":value.get("complete") is True,"checkpoint":value.get("checkpoint") if value.get("checkpoint") in allowed_phases else "other"}
    for key in ("installed_publication_component_qualified","refusal_controls_passed","bound_root_completion_verified",
                "prepared_owner_journal_reconciled","root_keys_withheld_from_children","previous_environment_settings_and_oauth_preserved"):
        if type(value.get(key)) is bool:result[key] = value[key]
    if type(value.get("qualification_credentials_issued")) is int and 0 <= value["qualification_credentials_issued"] <= 2:
        result["qualification_credentials_issued"] = value["qualification_credentials_issued"]
    if value.get("reason") in {"actual_publication_not_verified","bound_completion_not_verified",
            "fixture_interruption_failed_preserve_evidence","child_refused_review_retained_attempt","operator_resolution_binding_differs"}:
        result["reason"] = value["reason"]
    return result


def proof_predicates(case,service,timer):
    def positive(value):
        return isinstance(value,str) and value.isdecimal() and int(value) > 0
    invocation = case.get("unit_invocation_id","")
    return dict(case_complete=case.get("complete") is True,
        case_invocation_recorded=isinstance(invocation,str) and re.fullmatch(r"[a-f0-9]{32}",invocation) is not None,
        service_inactive=service.get("ActiveState") == "inactive",service_success=service.get("Result") == "success",
        service_exit_zero=service.get("ExecMainStatus") == "0",service_user_root=service.get("User") == "root",
        service_start_recorded=positive(service.get("ExecMainStartTimestampMonotonic")),
        invocation_matches=service.get("InvocationID","") in {"",invocation},
        timer_trigger_recorded=positive(timer.get("LastTriggerUSecMonotonic")))


def journal_scheduling_proof(rows,unit,invocation):
    """Only trusted PID-1 records may attest manager job completion.

    Fields/semantics: systemd v255 job.c and systemd.journal-fields(5).
    Never parse success out of MESSAGE text or expose raw record contents.
    """
    require(isinstance(invocation,str) and re.fullmatch(r"[a-f0-9]{32}",invocation),"recorded_invocation_required")
    events = {"service":{},"timer":{}}
    conflicts = False
    for row in rows:
        if not isinstance(row,dict) or (row.get("_PID"),row.get("_UID"),row.get("_COMM")) != ("1","0","systemd"):continue
        kind = next((kind for kind in events if row.get("UNIT") == unit+"."+kind),None)
        if kind is None or row.get("JOB_TYPE") != "start" or "JOB_RESULT" not in row:continue
        if row.get("JOB_RESULT") != "done":
            conflicts = True
            continue
        boot,stamp = row.get("_BOOT_ID"),row.get("__MONOTONIC_TIMESTAMP")
        if not (isinstance(boot,str) and re.fullmatch(r"[a-f0-9]{32}",boot)
                and isinstance(stamp,str) and stamp.isdecimal() and 0 < int(stamp) < 2**64):continue
        event_invocation = row.get("INVOCATION_ID","")
        if not isinstance(event_invocation,str):continue
        key = (boot,int(stamp),event_invocation)
        events[kind][key] = row
    unique = len(events["service"]) == len(events["timer"]) == 1
    same_boot,matched,elapsed = False,False,None
    if unique:
        service = next(iter(events["service"]))
        timer = next(iter(events["timer"]))
        same_boot = service[0] == timer[0]
        matched = service[2] == invocation
        if same_boot:elapsed = service[1]-timer[1]
    flags = dict(unique_service_completion=len(events["service"]) == 1,
        unique_timer_activation=len(events["timer"]) == 1,manager_invocation_matches=matched,
        same_boot=same_boot,configured_delay_elapsed=elapsed is not None and elapsed >= 15000000,
        no_conflicting_start_failures=not conflicts)
    return dict(verified=all(flags.values()),predicates=flags,
        service_success_events=len(events["service"]),timer_success_events=len(events["timer"]),
        elapsed_milliseconds=elapsed//1000 if elapsed is not None else None)


def publication_cases_complete(cases):
    return (len(cases) == 2 and {row["kind"] for row in cases} == {"manual","scheduled"}
        and all(row.get(key) is True for row in cases for key in ("complete","installed_publication_component_qualified",
            "bound_root_completion_verified","root_keys_withheld_from_children","refusal_controls_passed",
            "prepared_owner_journal_reconciled","previous_environment_settings_and_oauth_preserved")))


def inspect_existing(read,write=None,finish=False):
    previous = json.loads(read(EVIDENCE / "summary.json",0))
    require(previous.get("complete") is False and previous.get("reason") == "scheduled_publication_not_verified",
            "specific_failed_scheduling_attempt_required")
    ticket = json.loads(read(EVIDENCE / "scheduled-ticket.json",0))
    ident = ticket.get("id")
    require(isinstance(ident,str) and re.fullmatch(r"[a-f0-9]{16}",ident),"fixed_fixture_identifier_required")
    require(ticket == dict(id=ident,source_sha256=PUBLISHED_PROBE_SHA256)
        and hashlib.sha256((ARTIFACT / "qualify_launch_issuer_publication.py").read_bytes()).hexdigest() == PUBLISHED_PROBE_SHA256,
        "published_failed_probe_binding_required")
    unit = "ec-issuer-publication-"+ident
    require(previous.get("scheduled_unit") == unit+".service","scheduled_unit_binding_required")
    cases = []
    scheduled = {}
    for directory in EVIDENCE.iterdir():
        if not re.fullmatch(r"[a-f0-9]{16}",directory.name):continue
        require(len(cases) < 2,"bounded_existing_cases_required")
        try:value = json.loads(read(directory / "summary.json",0))
        except FileNotFoundError:continue
        if finish:require(value.get("fixture_id") == directory.name,"retained_case_identity_differs")
        cases.append(dict(kind="scheduled" if directory.name == ident else "manual",**safe_case_summary(value)))
        if directory.name == ident:scheduled = value
    service,timer = unit_metadata(unit+".service"),unit_metadata(unit+".timer")
    journal = subprocess.run(["/usr/bin/journalctl","--unit="+unit+".service","--unit="+unit+".timer","--no-pager","--lines=100","--output=json"],
        stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=10,env={"PATH":"/usr/bin:/bin","LANG":"C.UTF-8"})
    markers = {}
    rows = []
    if journal.returncode == 0 and len(journal.stdout) <= 131072:
        messages = []
        for line in journal.stdout.splitlines():
            try:
                row = json.loads(line)
                message = row.get("MESSAGE","")
            except (ValueError,AttributeError):continue
            rows.append(row)
            if isinstance(message,str):messages.append(message)
        for key,needle in {"permission_denied":"Permission denied","read_only_filesystem":"Read-only file system",
            "namespace_failure":"NAMESPACE","operation_not_permitted":"Operation not permitted",
            "preflight_refused":"issuer_publication_preflight_refused_no_secret_output"}.items():
            markers[key] = any(needle in message for message in messages)
    invocation = scheduled.get("unit_invocation_id","")
    journal_proof = journal_scheduling_proof(rows,unit,invocation) if re.fullmatch(r"[a-f0-9]{32}",invocation) else {"verified":False}
    result = dict(complete=True,stage="retained_scheduling_inspection",source_revision=BASE.name,scheduled_unit=unit+".service",
        cases=cases,scheduled_case_present=bool(scheduled),proof_predicates=proof_predicates(scheduled,service,timer),
        service_metadata=service,timer_metadata=timer,journal_markers=markers,journal_scheduling_proof=journal_proof,
        credentials_issued=0,profiles_changed=False,services_started=False,timers_created=False,evidence_changed=False,
        secret_values_printed=False,fleet_launch_approved=False)
    if finish:
        result["stage"] = "finish_retained_scheduled_publication"
        # Live properties may already describe unloaded transient units.
        # Never turn those default values into execution evidence.
        complete = publication_cases_complete(cases)
        result["complete"] = complete and journal_proof["verified"]
        result.update(installed_publication_component_qualified=complete,
            scheduled_publication_component_qualified=result["complete"],installed_issuer_qualified=False,
            scheduled_firing_qualified=False,running_gateway_reload_qualified=False,policy_entry_admission_qualified=False,
            production_renewal_timer_enabled=False,previous_failure_preserved=True,replayed_publication=False)
        # Read only policy admission metadata. No signing keys/profile access.
        driver = definitions(PACKAGE / "renew_fleet_credentials.py",PINS["renew_fleet_credentials.py"])
        driver["protected"](PACKAGE / "renew_fleet_credentials.py")
        policy_source = driver["sources"]()["fleet_credential_policy.py"]
        policy = driver["definitions"](policy_source,"retained_publication_policy")["load"](driver["POLICY"])
        require(not any(row["enabled"] for row in policy["profiles"]),"fleet_must_remain_disabled")
        result["fleet_policy_disabled"] = True
        if result["complete"]:
            require(write is not None,"protected_evidence_writer_required")
            result["evidence_changed"] = True
            result["evidence"] = str(EVIDENCE / "finish-existing.summary.json")
            write(EVIDENCE / "finish-existing.summary.json",json.dumps(result).encode())
        else:result["category"] = "retained_scheduling_evidence_insufficient_no_replay"
    print(json.dumps(result))
    return 0 if result["complete"] else 1


def main():
    require(os.geteuid() == 0,"fixed_root_operator_required")
    scheduled = len(sys.argv) == 3 and sys.argv[1] == "--scheduled"
    inspect = sys.argv[1:] == ["--inspect-existing"]
    finish = sys.argv[1:] == ["--finish-existing"]
    require(len(sys.argv) == 1 or scheduled or inspect or finish,"fixed_probe_action_required")
    os.umask(0o077)
    support_path = ARTIFACT / "recover_launch_graph_operator.py" if scheduled else Path(__file__).with_name("recover_launch_graph_operator.py")
    support = definitions(support_path,PINS["recover_launch_graph_operator.py"])
    read,write = support["read_file"],support["private_write"]
    if inspect or finish:return inspect_existing(read,write,finish=finish)
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
