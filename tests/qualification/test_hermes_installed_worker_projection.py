"""Worker-probe boundary checks, not installed delivery acceptance."""
import hashlib
import hmac
import importlib.util
import json
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
