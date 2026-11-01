"""Native ingress admission, source identity and immutable-result boundaries."""
import hashlib
import json
from pathlib import Path
import runpy

import pytest

DIRECTORY = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment'
QUAL = runpy.run_path(str(DIRECTORY / 'qualify_isolated_native_text_ingress.py'))


@pytest.mark.parametrize('damage',[None,'failed','wrong_uid_count','wrong_source','binding_drift','enabled','outside'])
def test_native_work_requires_the_completed_exact_transport_binding(monkeypatch,damage):
    scope = QUAL['prior_pass'].__globals__
    base = Path('/invented/root')
    artifact = base / 'transport'
    rows = [{'user':'invented-one'}, {'user':'invented-two'}]
    canonical = lambda value:json.dumps(value, sort_keys=True, separators=(',',':')).encode()
    context = dict(source_sha256=QUAL['TRANSPORT_QUAL_SHA'], transport_sha256='invented-transport-hash',
        bindings_sha256=hashlib.sha256(canonical(rows)).hexdigest(), evidence=str(base / 'operator-evidence/isolated-transport-invented'))
    summary = dict(complete=True, completed_cases=3, distinct_restricted_uids=2,
        operator_helper_sha256=QUAL['TRANSPORT_QUAL_SHA'], source_revision=base.name,
        binding_manifest_sha256=context['bindings_sha256'], kernel_authenticated_transport_qualified=True,
        all_admission_policies_preserved_disabled=True, fleet_launch_approved=False)
    if damage == 'failed':summary['complete'] = False
    if damage == 'wrong_uid_count':summary['distinct_restricted_uids'] = 1
    if damage == 'wrong_source':summary['operator_helper_sha256'] = 'wrong'
    if damage == 'binding_drift':summary['binding_manifest_sha256'] = 'wrong'
    if damage == 'enabled':summary['all_admission_policies_preserved_disabled'] = False
    if damage == 'outside':context['evidence'] = '/invented/outside/isolated-transport-invented'
    files = {artifact / 'context.private.json':canonical(context),
        artifact / 'selected-bindings.private.json':canonical(rows),
        Path(context['evidence']) / 'summary.json':canonical(summary)}
    monkeypatch.setitem(scope,'BASE',base)
    monkeypatch.setitem(scope,'TRANSPORT_ARTIFACT',artifact)
    operation = lambda:QUAL['prior_pass'](lambda path,*a:files[path], rows,
        dict(canonical=canonical,TRANSPORT_SHA='invented-transport-hash'))
    if damage:
        with pytest.raises(ValueError):operation()
    else:
        assert operation() == context['evidence']


@pytest.mark.parametrize('role',['frontend','worker'])
def test_owner_receipt_must_prove_its_own_role_and_exact_flags(role):
    flags = {'complete','identity_restricted','invented_text_roundtrip','profile_override_absent',
        'network_unused','real_profiles_unread'}
    if role == 'worker':
        flags |= {'native_sender_denial','duplicate_request_denial','native_clarification_preserved_and_resolved'}
    value = dict(dict.fromkeys(flags,True), role=role)
    assert QUAL['receipt'](value,role) == value
    for name in flags:
        altered = dict(value);altered[name] = False
        with pytest.raises(ValueError):QUAL['receipt'](altered,role)
    with pytest.raises(ValueError):QUAL['receipt'](dict(value,private_content='invented'),role)


@pytest.mark.parametrize('complete,tamper',[(True,False),(False,False),(True,True)])
def test_retained_native_result_is_returned_without_replaying_any_probe(monkeypatch,tmp_path,capsys,complete,tamper):
    scope = QUAL['main'].__globals__
    base = tmp_path / 'base'
    artifact = base / 'artifact';artifact.mkdir(parents=True)
    evidence = base / 'operator-evidence/isolated-native-text-invented';evidence.mkdir(parents=True)
    source = b'invented-source';digest = hashlib.sha256(source).hexdigest()
    (artifact / 'qualify_isolated_native_text_ingress.py').write_bytes(source)
    for name in QUAL['PUBLIC']:
        (artifact / name).write_bytes((DIRECTORY / name).read_bytes())
    bindings = b'invented-private-bindings'
    (artifact / 'selected-bindings.private.json').write_bytes(bindings if not tamper else b'altered')
    context = dict(source_sha256=digest,component_hashes=QUAL['PUBLIC'],native_source_hashes=QUAL['NATIVE'],
        bindings_sha256=hashlib.sha256(bindings).hexdigest(),evidence=str(evidence))
    (artifact / 'context.private.json').write_text(json.dumps(context))
    result = dict(complete=complete,operator_helper_sha256=digest,source_revision=base.name,
        binding_manifest_sha256=context['bindings_sha256'])
    (evidence / 'summary.json').write_text(json.dumps(result))
    monkeypatch.setitem(scope,'BASE',base);monkeypatch.setitem(scope,'ARTIFACT',artifact)
    monkeypatch.setitem(scope,'_verified_source_bytes',source)
    monkeypatch.setattr(QUAL['os'],'geteuid',lambda:0)
    monkeypatch.setattr(QUAL['os'],'umask',lambda mask:None)
    monkeypatch.setattr(QUAL['resource'],'setrlimit',lambda *a:None)
    transport = runpy.run_path(str(DIRECTORY / 'qualify_isolated_gateway_transport.py'))
    def fixture_definitions(path, digest):
        if path.name == 'qualify_isolated_gateway_transport.py':
            return transport
        assert path.name == 'recover_launch_graph_operator.py'
        return dict(read_file=lambda path,*a:path.read_bytes(),
            private_write=lambda *a:pytest.fail('retained evidence rewritten'))
    monkeypatch.setitem(scope,'definitions',fixture_definitions)
    monkeypatch.setitem(scope,'run_case',lambda *a:pytest.fail('completed or failed probe replayed'))
    if tamper:
        with pytest.raises(ValueError):QUAL['main']()
    else:
        assert QUAL['main']() == (0 if complete else 1)
        assert json.loads(capsys.readouterr().out) == result


def test_all_public_components_and_controller_are_pinned_to_the_reviewed_bytes():
    assert set(QUAL['PUBLIC']) == {'isolated_gateway_transport.py','isolated_native_text_ingress.py','probe_isolated_native_text_ingress.py'}
    for name, digest in QUAL['PUBLIC'].items():
        assert hashlib.sha256((DIRECTORY / name).read_bytes()).hexdigest() == digest
    controller = runpy.run_path(str(DIRECTORY / 'launch_control.py'))
    assert controller['NATIVE_TEXT_INGRESS_SHA'] == hashlib.sha256((DIRECTORY / 'qualify_isolated_native_text_ingress.py').read_bytes()).hexdigest()
