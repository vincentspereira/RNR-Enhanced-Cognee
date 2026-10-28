"""Inspect the stopped zero-effect REA V2 job without an effectful retry.

Repeat only the frozen read-only model-binding guards when their checkpoint
proves they failed before settings capture. No key, hash of a key, raw exception,
profile contents, process arguments or child stdout is published.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import resource
import tempfile

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
ARTIFACT = BASE / 'operator-rea-main-programs-v2'
FAILED_SHA = 'bce3399d071eb69f9d1a4a95dd52a6aab255d67f6dd96a1a71d739fcf85e3a41'
EXPECTED = BASE / 'operator-evidence/rea-main-programs-yhw1c8p4'
PHASES = ('model_binding', 'current_settings_capture', 'public_programs',
          'isolated_program_execution', 'new_candidate', 'configured_backup',
          'configured_restore', 'source_freshness')
KINDS = {'ValueError', 'PermissionError', 'FileNotFoundError', 'OSError',
         'RuntimeError', 'TypeError', 'KeyError', 'CalledProcessError', 'TimeoutExpired'}


def require(value):
    if not value:
        raise ValueError('rea_continuation_inspection_refused')


def definitions(path, digest):
    raw = path.read_bytes()
    require(0 < len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == digest)
    result = {'__name__': 'verified_rea_continuation_inspection', '__file__': str(path)}
    exec(compile(raw, '<verified-rea-continuation-inspection>', 'exec'), result)
    return result


def retained(original, read):
    context = json.loads(read(ARTIFACT / 'context.private.json', 0))
    require(context.get('source_sha256') == FAILED_SHA and context.get('evidence') == str(EXPECTED))
    result = json.loads(read(EXPECTED / 'finish.summary.json', 0))
    require(result.get('evidence') == str(EXPECTED) and result.get('source_revision') == BASE.name
            and result.get('operator_helper_sha256') == FAILED_SHA and result.get('complete') is False
            and result.get('operator_job_stopped') is True and result.get('credentials_issued') == 0
            and result.get('encrypted_generations_created') == 0 and result.get('prior_failure_preserved') is True
            and result.get('all_admission_policies_preserved_disabled') is True
            and result.get('category') == 'rea_main_programs_incomplete_preserve_evidence_no_automatic_retry'
            and result.get('error_kind') == 'ValueError'
            and re.fullmatch('[a-f0-9]{32}', result.get('invocation_id', '')) is not None
            and all(result.get(key) is False for key in (
                'source_profiles_changed', 'source_programs_changed', 'previous_candidates_changed',
                'candidate_promoted', 'daily_backup_registry_changed', 'canonical_memory_edits',
                'chat_model_called', 'rea_server_started', 'fleet_launch_approved', 'production_renewal_timer_enabled')))
    require(original['stopped'](original['metadata'](original['UNIT'])))
    markers = {}
    for phase in PHASES:
        path = EXPECTED / (phase + '.started.json')
        markers[phase] = os.path.lexists(path)
        if markers[phase]:
            require(json.loads(read(path, 0)) == {'phase': phase})
    require(not any(markers[phase] for phase in PHASES[2:])
            and not any(os.path.lexists(ARTIFACT / (name + '.tar')) for name in ('ghidra', 'java')))
    return context, markers


def observe_binding(c, driver, read, evidence):
    """Observe the exact frozen checks; intercept only their private receipts."""
    result = dict(inspection_complete=True, model_binding_verified=False,
                  source_route_observed=False, fixture_binding_observed=False,
                  private_receipt_write_suppressed=True)
    original_owner = c['owner']
    source_digest = None

    def observe_owner(account, source, packet, **kwargs):
        nonlocal source_digest
        value, body = original_owner(account, source, packet, **kwargs)
        if packet == {'mode': 'read_source'}:
            result['source_route_observed'] = True
            result['source_receipt_shape_matches'] = (
                isinstance(value, dict) and set(value) == {'complete', 'key', 'endpoint_path'} and not body)
            result['source_endpoint_matches'] = isinstance(value, dict) and value.get('endpoint_path') == '/api/coding/paas/v4'
            if result['source_receipt_shape_matches'] and isinstance(value.get('key'), str):
                source_digest = hashlib.sha256(value['key'].encode()).hexdigest()
        elif set(packet) == {'completed_ns'}:
            result['fixture_binding_observed'] = True
            result['fixture_receipt_shape_matches'] = (
                isinstance(value, dict) and set(value) == {'complete', 'model_key_sha256', 'fixture_unchanged_since_receipt'} and not body)
            result['fixture_unchanged_since_receipt'] = (
                isinstance(value, dict) and value.get('fixture_unchanged_since_receipt') is True)
            result['qualified_key_matches_current_source'] = (
                isinstance(value, dict) and source_digest is not None and value.get('model_key_sha256') == source_digest)
        else:
            raise ValueError('unexpected_readonly_owner_packet')
        return value, body

    def suppress_write(path, raw):
        require(path == evidence / 'qualified-model-binding.private.json')
        value = json.loads(raw)
        require(set(value) == {'complete', 'model_key_sha256', 'fixture_unchanged_since_receipt'}
                and value.get('complete') is True and value.get('fixture_unchanged_since_receipt') is True)
        result['private_receipt_verified'] = True

    try:
        c['owner'] = observe_owner
        key = c['runtime_model'](driver, read, suppress_write, evidence)
        require(isinstance(key, str) and source_digest is not None
                and hashlib.sha256(key.encode()).hexdigest() == source_digest)
        del key
        result['model_binding_verified'] = True
    except Exception as error:
        kind = type(error).__name__
        result['error_kind'] = kind if kind in KINDS else 'other'
        frames = []
        tb = error.__traceback__
        while tb:
            name = tb.tb_frame.f_code.co_name
            if name in {'runtime_model', 'verify_runtime', 'require', 'definitions', 'read_file', 'owner'}:
                frames.append(dict(function=name, line=tb.tb_lineno))
            tb = tb.tb_next
        result['public_helper_frames'] = frames[-8:]
        diagnostic = getattr(error, 'owner_diagnostic', None)
        if isinstance(diagnostic, dict):
            result['owner_error_kind'] = diagnostic.get('error_kind') if diagnostic.get('error_kind') in KINDS else 'other'
            phase = diagnostic.get('phase')
            result['owner_phase'] = phase if phase in {'identity', 'source_configuration', 'configuration', 'source_read'} else 'other'
    finally:
        c['owner'] = original_owner
        source_digest = None
    return result


def main():
    require(os.geteuid() == 0)
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    original = definitions(ARTIFACT / 'continue_rea_main_programs.py', FAILED_SHA)
    c = original['common']()
    read, write = original['support'](c)
    context, markers = retained(original, read)
    before = {name: read(EXPECTED / name, 0) for name in ('summary.json', 'finish.summary.json')}
    report = dict(complete=True, stage='retained_rea_continuation_inspection', source_revision=BASE.name,
                  previous_evidence=str(EXPECTED), checkpoint_markers=markers,
                  credentials_issued=0, profiles_changed=False, services_started=False,
                  programs_staged=False, model_called=False, memory_api_called=False,
                  effectful_retry=False, prior_failure_preserved=True, fleet_launch_approved=False)
    if markers['model_binding'] and not markers['current_settings_capture']:
        driver = c['legacy']()
        report['readonly_model_binding'] = observe_binding(c, driver, read, EXPECTED)
    else:
        report['readonly_model_binding'] = dict(inspection_complete=False, not_reexecuted=True)
    require(all(read(EXPECTED / name, 0) == raw for name, raw in before.items()))
    retained(original, read)
    evidence = Path(tempfile.mkdtemp(prefix='rea-continuation-inspection-', dir=BASE / 'operator-evidence'))
    report['evidence'] = str(evidence)
    write(evidence / 'summary.json', json.dumps(report, sort_keys=True).encode())
    print(json.dumps(report, sort_keys=True), flush=True)
    return 0
