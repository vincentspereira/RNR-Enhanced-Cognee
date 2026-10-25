"""Worker-probe boundary checks, not installed delivery acceptance."""
import hashlib
import hmac
import importlib.util
from io import BytesIO
import json
import sys
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment/qualify_installed_worker_projection.py"
spec = importlib.util.spec_from_file_location("installed_worker_projection",SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def test_probe_key_matches_real_pipeline_scoped_identity_contract():
    key,pipeline,project,ident = "invented-key","hermes","wp_invented","invented-record"
    raw = json.dumps([pipeline,"record","qualification",project,ident],separators=(",",":")).encode()
    assert helper.record_cache_key(key,pipeline,project,ident) == "ec:hermes:"+hmac.new(key.encode(),raw,hashlib.sha256).hexdigest()
    assert helper.record_cache_key(key,pipeline,"other",ident) != helper.record_cache_key(key,pipeline,project,ident)


@pytest.mark.parametrize("violation",[None,"wrong-id","unqueried","no-graph","plain-cache","leaked-text"])
def test_delivery_requires_actual_vector_graph_and_encrypted_cache(violation):
    recall = {"vector_index":"queried","results":[{"id":"invented"}]}
    graph = {"paths":[{"invented":True}]}
    cached = b'{"payload":"enc2:invented-ciphertext"}'
    if violation == "wrong-id": recall["results"][0]["id"] = "other"
    if violation == "unqueried": recall["vector_index"] = "unavailable"
    if violation == "no-graph": graph["paths"] = []
    if violation == "plain-cache": cached = b'{"payload":"plain"}'
    if violation == "leaked-text": cached = b'{"payload":"enc2:invented","unexpected":"invented-source-text"}'
    assert helper.projection_ready("invented",recall,graph,cached,"invented-source-text") is (violation is None)


def test_ordinary_user_refused_before_private_reads(monkeypatch):
    monkeypatch.setattr(helper.os,"geteuid",lambda:1000)
    monkeypatch.setattr(helper,"definitions",lambda *a:pytest.fail("must not read supporting code"))
    with pytest.raises(ValueError,match="local_root_operator_required"):
        helper.main()


def test_all_shared_support_sources_match_pins():
    for name,digest in helper.SOURCES.items():
        assert hashlib.sha256(SOURCE.with_name(name).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize("finish",[False,True])
def test_inspection_or_finish_refuses_mutation_without_verified_delivery(monkeypatch,capsys,finish):
    monkeypatch.setattr(helper.os,"geteuid",lambda:0)
    previous = {"project":"wp_10df177d41ceef89","record_id":"c85b599e-69b4-46f4-ac8d-9f3848bc3d3b"}
    worker = {"INDEX_VALKEY_URL":"redis://invented:invented-private-cache@127.0.0.1:28537/0",
              "ENHANCED_INDEX_KEY":"invented-private-index"}
    calls = []
    def definitions(name):
        if name == "recover_launch_graph_operator.py":
            return {"read_file":lambda path,owner:json.dumps(previous if path.name == "summary.json" else worker).encode()}
        if name == "provision_pilot_access.py":
            return {"load_signing_key":lambda:"invented-private-signing", "sign_claims":lambda *a:"invented-ordinary-token"}
        return {"cache_call":lambda *a:("refused",None)}
    def api(token,method,path,body=None):
        assert method == "GET" and path.endswith("/status") or method == "POST" and path in {
            "/v1/memories/recall","/v1/memories/connections"}
        calls.append((method,path))
        return 200,{"index":{"worker_state":"running","worker_available":True},"pending_change_events":0,
                    "vector_index":"queried","results":[{"id":previous["record_id"]}],"paths":[{}]}
    monkeypatch.setattr(helper,"definitions",definitions)
    monkeypatch.setattr(helper,"public_index_settings",lambda:{"pipeline":"hermes"})
    monkeypatch.setattr(helper,"cache_get",lambda *a:("refused",None))
    monkeypatch.setattr(helper,"api",api)
    assert helper.inspect_existing(finish=finish) == (1 if finish else 0)
    output = capsys.readouterr().out
    receipt = json.loads(output)
    assert receipt["cache_get_refused"] is True and receipt["memory_written"] is False
    assert len(calls) == 3
    assert "invented-private" not in output


def test_realistic_encrypted_embedding_cache_reply_exceeds_small_probe_limit():
    raw = json.dumps({"payload":"enc2:"+"A"*12000}).encode()
    wire = b"$"+str(len(raw)).encode()+b"\r\n"+raw+b"\r\n"
    assert helper.cache_bulk_reply(BytesIO(wire)) == ("bulk",raw)
    small_reader = helper.definitions("install_launch_cache_operator.py")["read_reply"]
    with pytest.raises(ValueError,match="bounded_cache_response_required"):
        small_reader(BytesIO(wire))


@pytest.mark.parametrize("wire",[b"$262145\r\n",b"$12\r\nshort\r\n",b"+unexpected\r\n"])
def test_larger_cache_reader_still_refuses_oversize_truncation_and_wrong_type(wire):
    with pytest.raises(ValueError):
        helper.cache_bulk_reply(BytesIO(wire))


def test_cache_reader_suppresses_private_error_text():
    assert helper.cache_bulk_reply(BytesIO(b"-NOPERM invented-private-details\r\n")) == ("refused",None)


@pytest.mark.parametrize("complete",[False,"true",1])
def test_post_rotation_probe_requires_strict_completed_rotation_receipts(monkeypatch,complete):
    monkeypatch.setattr(helper.os,"geteuid",lambda:0)
    monkeypatch.setattr(sys,"argv",["probe","--post-rotation"])
    monkeypatch.setattr(helper,"definitions",lambda name:{"read_file":lambda *args:json.dumps({"complete":complete}).encode(),
        "private_write":lambda *args:pytest.fail("must not write before prerequisites")})
    with pytest.raises(ValueError,match="completed_credential_rotations_required"):
        helper.main()


@pytest.mark.parametrize("missing",["application-signing-rotation","postgres-legacy-login-retirement","derived-legacy-login-retirement"])
def test_post_retirement_requires_each_completed_retirement_before_any_new_probe(monkeypatch,missing):
    monkeypatch.setattr(helper.os,"geteuid",lambda:0)
    monkeypatch.setattr(sys,"argv",["probe","--post-retirement"])
    def read(path,owner):
        return json.dumps({"complete":path.parent.name != missing}).encode()
    monkeypatch.setattr(helper,"definitions",lambda name:{"read_file":read,
        "private_write":lambda *args:pytest.fail("must not write before retirement gates")})
    with pytest.raises(ValueError,match="completed_login_retirements_required"):
        helper.main()
