"""Fixed synthetic publication/scheduler boundaries, without host execution."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment/qualify_launch_issuer_publication.py"
spec = importlib.util.spec_from_file_location("issuer_publication_probe",SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def test_source_pins_match_reviewed_components():
    for name,digest in helper.PINS.items():assert hashlib.sha256(SOURCE.with_name(name).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize("ident",["../escape","a"*15,"g"*16,"a"*16+";ignored"])
def test_fixture_and_timer_refuse_caller_paths_or_nonfixed_identifiers(ident):
    with pytest.raises(ValueError):helper.fixture_entry(ident,None,{})
    with pytest.raises(ValueError):helper.timer_command(ident)


def test_one_shot_scheduler_uses_root_source_and_minimum_transition_capabilities():
    args = helper.timer_command("a"*16)
    assert args[:2] == ["/usr/bin/systemd-run","--quiet"]
    assert "--on-active=15s" in args and "--property=Restart=no" in args
    assert "--property=NoNewPrivileges=yes" in args
    assert "--property=CapabilityBoundingSet=CAP_SETUID CAP_SETGID CAP_CHOWN" in args
    assert args[-3:] == [str(helper.ARTIFACT / SOURCE.name),"--scheduled","a"*16]
    assert not any("--enable" in value or "fleet-credentials" in value for value in args)


def test_nonroot_stops_before_any_protected_read(monkeypatch):
    monkeypatch.setattr(helper.os,"geteuid",lambda:1000)
    with pytest.raises(ValueError,match="fixed_root_operator_required"):helper.main()


def test_retained_inspection_never_replays_cases_or_prints_private_logs(monkeypatch,tmp_path,capsys):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    artifact = tmp_path / "artifact"
    artifact.mkdir()
    frozen = b"invented-frozen-public-probe"
    (artifact / SOURCE.name).write_bytes(frozen)
    monkeypatch.setattr(helper,"PUBLISHED_PROBE_SHA256",hashlib.sha256(frozen).hexdigest())
    monkeypatch.setattr(helper,"EVIDENCE",evidence)
    monkeypatch.setattr(helper,"ARTIFACT",artifact)
    ident = "a"*16
    unit = "ec-issuer-publication-"+ident
    (evidence / "summary.json").write_text(json.dumps(dict(complete=False,reason="scheduled_publication_not_verified",scheduled_unit=unit+".service")))
    (evidence / "scheduled-ticket.json").write_text(json.dumps(dict(id=ident,source_sha256=helper.PUBLISHED_PROBE_SHA256)))
    case = evidence / ident
    case.mkdir()
    (case / "summary.json").write_text(json.dumps(dict(complete=False,checkpoint="installed_publication_child",unexpected="invented-private-value")))
    monkeypatch.setattr(helper,"unit_metadata",lambda name:dict(ActiveState="failed",ExecMainStatus="1",User="root"))
    monkeypatch.setattr(helper.subprocess,"run",lambda *args,**kwargs:SimpleNamespace(returncode=0,
        stdout=b'{"MESSAGE":"Permission denied invented-private-log"}\n'))
    monkeypatch.setattr(helper,"publish_case",lambda *args:pytest.fail("must not replay publication"))
    before = {path:path.read_bytes() for path in evidence.rglob("*") if path.is_file()}
    assert helper.inspect_existing(lambda path,owner:path.read_bytes()) == 0
    output = capsys.readouterr().out
    assert "invented-private" not in output
    result = json.loads(output)
    assert result["journal_markers"]["permission_denied"] is True
    assert result["proof_predicates"]["case_complete"] is False
    assert result["credentials_issued"] == 0 and result["evidence_changed"] is False
    assert before == {path:path.read_bytes() for path in evidence.rglob("*") if path.is_file()}


def test_case_summary_omits_unknown_checkpoint_and_private_fields():
    result = helper.safe_case_summary(dict(complete=False,checkpoint="invented-private-data",reason="invented-private-reason",private="invented"))
    assert result == dict(complete=False,checkpoint="other")


@pytest.mark.parametrize("failure",[None,"untrusted_pid","untrusted_uid","wrong_unit","wrong_invocation",
    "wrong_boot","too_early","failed_job","missing_service","ambiguous_service","fake_message"])
def test_retained_journal_requires_unique_trusted_manager_jobs_bound_to_case_and_delay(failure):
    unit = "ec-issuer-publication-"+"a"*16
    common = dict(_PID="1",_UID="0",_COMM="systemd",JOB_TYPE="start",JOB_RESULT="done",_BOOT_ID="b"*32)
    timer = dict(common,UNIT=unit+".timer",__MONOTONIC_TIMESTAMP="1000000",INVOCATION_ID="c"*32)
    service = dict(common,UNIT=unit+".service",__MONOTONIC_TIMESTAMP="17000000",INVOCATION_ID="d"*32)
    rows = [timer,service]
    if failure == "untrusted_pid":service["_PID"] = "1000"
    if failure == "untrusted_uid":service["_UID"] = "1000"
    if failure == "wrong_unit":service["UNIT"] = "another.service"
    if failure == "wrong_invocation":service["INVOCATION_ID"] = "e"*32
    if failure == "wrong_boot":service["_BOOT_ID"] = "e"*32
    if failure == "too_early":service["__MONOTONIC_TIMESTAMP"] = "15000000"
    if failure == "failed_job":rows.append(dict(service,JOB_RESULT="failed"))
    if failure == "missing_service":rows = [timer]
    if failure == "ambiguous_service":rows.append(dict(service,__MONOTONIC_TIMESTAMP="18000000"))
    if failure == "fake_message":rows = [dict(MESSAGE="systemd job succeeded root timer done")]
    result = helper.journal_scheduling_proof(rows,unit,"d"*32)
    assert result["verified"] is (failure is None)
    assert "d"*32 not in json.dumps(result) and "b"*32 not in json.dumps(result)
    if failure is None:assert result["elapsed_milliseconds"] == 16000


def test_retained_case_completion_requires_both_kinds_and_all_safety_receipts():
    fields = ("complete","installed_publication_component_qualified","bound_root_completion_verified",
        "root_keys_withheld_from_children","refusal_controls_passed","prepared_owner_journal_reconciled",
        "previous_environment_settings_and_oauth_preserved")
    cases = [dict(kind=kind,**{key:True for key in fields}) for kind in ("manual","scheduled")]
    assert helper.publication_cases_complete(cases)
    assert not helper.publication_cases_complete(cases[:1])
    assert not helper.publication_cases_complete([cases[0],cases[0]])
    for key in fields:
        assert not helper.publication_cases_complete([cases[0],dict(cases[1],**{key:False})])


def test_finish_adds_separate_proof_without_replay_after_units_are_unloaded(monkeypatch,tmp_path,capsys):
    evidence,artifact = tmp_path / "evidence",tmp_path / "artifact"
    evidence.mkdir()
    artifact.mkdir()
    frozen = b"invented-frozen-public-source"
    (artifact / SOURCE.name).write_bytes(frozen)
    monkeypatch.setattr(helper,"EVIDENCE",evidence)
    monkeypatch.setattr(helper,"ARTIFACT",artifact)
    monkeypatch.setattr(helper,"PUBLISHED_PROBE_SHA256",hashlib.sha256(frozen).hexdigest())
    ident = "a"*16
    unit = "ec-issuer-publication-"+ident
    (evidence / "summary.json").write_text(json.dumps(dict(complete=False,reason="scheduled_publication_not_verified",scheduled_unit=unit+".service")))
    (evidence / "scheduled-ticket.json").write_text(json.dumps(dict(id=ident,source_sha256=helper.PUBLISHED_PROBE_SHA256)))
    fields = ("complete","installed_publication_component_qualified","bound_root_completion_verified","refusal_controls_passed",
        "root_keys_withheld_from_children","prepared_owner_journal_reconciled","previous_environment_settings_and_oauth_preserved")
    for case_id in (ident,"f"*16):
        case = evidence / case_id
        case.mkdir()
        (case / "summary.json").write_text(json.dumps(dict(fixture_id=case_id,checkpoint="complete",unit_invocation_id="d"*32,
            **{key:True for key in fields})))
    before = {path:path.read_bytes() for path in evidence.rglob("*") if path.is_file()}
    common = dict(_PID="1",_UID="0",_COMM="systemd",_BOOT_ID="b"*32,JOB_TYPE="start",JOB_RESULT="done",MESSAGE="invented-private-message")
    rows = [dict(common,UNIT=unit+".timer",__MONOTONIC_TIMESTAMP="1000000",INVOCATION_ID="c"*32),
            dict(common,UNIT=unit+".service",__MONOTONIC_TIMESTAMP="17000000",INVOCATION_ID="d"*32)]
    def run(args,**kwargs):
        assert args[0] == "/usr/bin/journalctl"
        return SimpleNamespace(returncode=0,stdout=b"\n".join(json.dumps(row).encode() for row in rows))
    monkeypatch.setattr(helper.subprocess,"run",run)
    monkeypatch.setattr(helper,"unit_metadata",lambda name:dict(LoadState="not-found",User="",LastTriggerUSecMonotonic="0"))
    driver = dict(protected=lambda *args:None,sources=lambda:{"fleet_credential_policy.py":b"public"},POLICY=Path("/invented/policy"),
        definitions=lambda *args:{"load":lambda *args:{"profiles":[{"enabled":False}]}})
    monkeypatch.setattr(helper,"definitions",lambda *args:driver)
    monkeypatch.setattr(helper,"publish_case",lambda *args:pytest.fail("must not replay"))
    def write(path,raw):
        fd = os.open(path,os.O_WRONLY | os.O_CREAT | os.O_EXCL,0o600)
        with os.fdopen(fd,"wb") as stream:stream.write(raw)
    assert helper.inspect_existing(lambda path,owner:path.read_bytes(),write,finish=True) == 0
    output = capsys.readouterr().out
    assert "invented-private-message" not in output
    result = json.loads(output)
    assert result["complete"] and result["scheduled_publication_component_qualified"]
    assert result["credentials_issued"] == 0 and result["services_started"] is False
    assert result["previous_failure_preserved"] and result["replayed_publication"] is False
    assert all(path.read_bytes() == raw for path,raw in before.items())
    assert (evidence / "finish-existing.summary.json").stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("failure",[None,"trigger","exit","identity","invocation","completion"])
def test_scheduled_proof_requires_timer_trigger_service_exit_root_and_bound_invocation(failure):
    case = dict(complete=True,unit_invocation_id="a"*32)
    service = dict(ActiveState="inactive",Result="success",ExecMainStatus="0",User="root",
        ExecMainStartTimestampMonotonic="123",InvocationID="")
    timer = dict(LastTriggerUSecMonotonic="120")
    if failure == "trigger":timer["LastTriggerUSecMonotonic"] = "0"
    if failure == "exit":service["ExecMainStatus"] = "1"
    if failure == "identity":service["User"] = "invented"
    if failure == "invocation":service["InvocationID"] = "b"*32
    if failure == "completion":case["complete"] = False
    if failure:
        with pytest.raises(ValueError):helper.scheduled_proof(case,service,timer)
    else:helper.scheduled_proof(case,service,timer)


@pytest.mark.parametrize("published",[True,False])
def test_publication_withholds_key_binds_before_child_and_closes_only_success(monkeypatch,tmp_path,published):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    monkeypatch.setattr(helper,"EVIDENCE",evidence)
    monkeypatch.setattr(helper,"FIXTURES",fixtures)
    account = SimpleNamespace(pw_name="invented",pw_uid=os.geteuid(),pw_gid=os.getegid(),pw_dir="/invented/home")
    monkeypatch.setattr(helper.pwd,"getpwnam",lambda name:account)
    policy = dict(ORIGIN="http://127.0.0.1:28080",EXECUTABLE="/invented/python")
    root_key = b"invented-root-key-never-sent-to-owner"
    core = {"load_signing_key":lambda:root_key,"sign_claims":lambda claims,key:"invented-old-token",
        "make_bundle":lambda key,now:{"token":"invented-new-token"},
        "open_directory":lambda path,owners:os.open(path,os.O_RDONLY | os.O_DIRECTORY)}
    native = helper.definitions(SOURCE.with_name("renew_fleet_credentials.py"),helper.PINS["renew_fleet_credentials.py"])
    driver = {key:native[key] for key in ("ledger_write","binding_digest","SOURCES")}
    driver.update(protected=lambda path:None,sources=lambda:{})
    def initialize(account,data):
        assert root_key.decode() not in json.dumps(data)
        assert data["phase"] == "prepared"
        assert not any(data["entry"][flag] for flag in ("enabled","reload_qualified","launch_binding_qualified","backup_qualified","os_boundary_qualified"))
    def child(entry,bundle,source):
        assert root_key.decode() not in json.dumps(bundle)
        assert len(list(driver["LEDGER"].glob("*.started.json"))) == 1
        assert len(list(driver["LEDGER"].glob("*.issued.json"))) == 1
        return dict(credential_published=published,interrupted_attempts_reconciled=1)
    driver["run_child"] = child
    driver["attempt_closed"] = lambda core,entry,path:len(list(driver["LEDGER"].glob("*.done.json"))) == 1
    result = helper.publish_case("a"*16,driver,{"initialize_fixture":initialize},core,policy,lambda path,raw:path.write_bytes(raw))
    assert result["complete"] is published
    assert len(list(driver["LEDGER"].glob("*.done.json"))) == int(published)
    assert root_key.decode() not in (evidence / ("a"*16) / "summary.json").read_text()
    assert result["qualification_credentials_issued"] == 2
