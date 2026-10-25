"""Fixed counters/public frames and source preservation; no host credentials."""
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment/diagnose_launch_gateway_network.py"
spec = importlib.util.spec_from_file_location("gateway_network_diagnostic",SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def good():
    return dict(complete=True,credentials_issued=0,original_fixture_changed=False,memory_records_written=False,
        model_called=False,network_counts={"memory":2,"forbidden":0},blocked_events=[],
        existing_credential_authenticated=True,invalid_control_denied=True,cache_change_observed=True)


def test_original_failed_source_and_file_support_are_exact():
    assert hashlib.sha256(SOURCE.with_name("qualify_launch_gateway_renewal.py").read_bytes()).hexdigest() == helper.ORIGINAL_SHA256
    assert hashlib.sha256(SOURCE.with_name("recover_launch_graph_operator.py").read_bytes()).hexdigest() == helper.SHARED_SHA256


def test_guard_keeps_same_boundary_and_never_serializes_destinations(monkeypatch,tmp_path):
    calls = []
    monkeypatch.setattr(helper.socket.socket,"connect",lambda sock,address:calls.append(address))
    monkeypatch.setattr(helper.socket,"getaddrinfo",lambda host,port,*a,**kw:None)
    counts,events = helper.guarded_network(tmp_path)
    helper.socket.socket.connect(None,("127.0.0.1",28080))
    with pytest.raises(RuntimeError):helper.socket.socket.connect(None,"/invented-private/socket")
    with pytest.raises(RuntimeError):helper.socket.getaddrinfo("invented-private-model.invalid",443)
    assert counts == {"memory":1,"forbidden":2}
    assert calls == [("127.0.0.1",28080)]
    raw = json.dumps(events)
    assert "invented-private" not in raw
    report = good()
    report.update(network_counts=counts,blocked_events=events)
    assert helper.validate_diagnostic(report,tmp_path) == report


@pytest.mark.parametrize("field,value",[("credentials_issued",1),("original_fixture_changed",True),
    ("model_called",True),("memory_records_written",True),("unexpected_private_field","invented")])
def test_diagnostic_rejects_mutation_or_private_receipts(field,value,tmp_path):
    report = good()
    report[field] = value
    with pytest.raises(ValueError):helper.validate_diagnostic(report,tmp_path)


def test_unbounded_counters_and_private_stack_paths_refused(tmp_path):
    report = good()
    report["network_counts"]["memory"] = 1001
    with pytest.raises(ValueError):helper.validate_diagnostic(report,tmp_path)
    report = good()
    report["blocked_events"] = [dict(operation="connect",destination_kind="tuple",host_is_memory=False,
        port_is_memory=False,host_is_bytes=False,port_is_text=False,phase="native_construction",
        source_frames=[dict(file="/invented/private/profile.py",line=1)])]
    with pytest.raises(ValueError,match="private_frame_path_refused"):helper.validate_diagnostic(report,tmp_path)


def test_nonroot_parent_refused_before_reading_operator_evidence(monkeypatch):
    monkeypatch.setattr(helper.os,"geteuid",lambda:1000)
    with pytest.raises(ValueError,match="fixed_root_operator_required"):helper.main()


def test_root_child_stops_before_source_or_profile_access(monkeypatch):
    monkeypatch.setattr(helper.os,"geteuid",lambda:0)
    monkeypatch.setattr(helper.pwd,"getpwnam",lambda name:SimpleNamespace(pw_uid=993))
    monkeypatch.setattr(helper,"definitions",lambda *args:pytest.fail("must not load source before dropping identity"))
    with pytest.raises(ValueError,match="restricted_owner_required"):helper.child({})
