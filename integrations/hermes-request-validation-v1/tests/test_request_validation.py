"""Request admission regression: genuine CPU ONNX/LanceDB, synthetic homes.

Only the host config loader is stubbed by the copied timing helper; this is not
full plugin admission or host prompt-dispatch acceptance. Session IDs use the
public string contract, not hostile Python objects or an authentication claim.
"""
import sys

import pytest
from enhanced_cognee_hermes import EnhancedCogneeProvider
from test_chat_switch_safety import QUERY, A, B, gated_call, manager, open_real, record

from src.hermes_memory.runtime import EnhancedMemoryEngine


def snapshot(p, m):
    with p._state_lock:
        return (p._request_id, p._generation, p._session_id, p.recall_status(),
                p.diagnostics(), m.describe_recall(), tuple(p._sessions.items()))


@pytest.mark.parametrize('rejected_session', ['a', 'unknown-physical-session'])
@pytest.mark.parametrize('stage', ['published', 'inflight'])
def test_rejected_string_session_preserves_current_ownership(tmp_path, rejected_session, stage):
    p = open_real(tmp_path / 'admission')
    m = manager(p)
    p.on_session_switch('b', gateway_session_key='beta')
    try:
        valid = m.prefetch_all(QUERY, session_id='b')
        assert B in valid and A not in valid and m.describe_recall()
        observations = []

        def reject():
            before = snapshot(p, m)
            searches = []
            oldtrace = sys.gettrace()

            def trace(frame, event, arg):
                if event == 'call' and frame.f_code is EnhancedMemoryEngine.search.__code__:
                    searches.append(frame.f_locals.get('scope'))
                return trace

            try:
                sys.settrace(trace)
                rejected = p.prefetch(QUERY, session_id=rejected_session)
            finally:
                sys.settrace(oldtrace)
            after = snapshot(p, m)
            observations.append({'rejected': rejected, 'search_entries': len(searches),
                                 'unchanged': after == before})
            assert rejected == '' and searches == []
            assert after == before, 'Rejected request mutated current ownership/status'
            assert p.recall_status() is before[3]

        if stage == 'inflight':
            result = gated_call(p, 'RecallStatus("Enhanced Cognee", len(entries))', reject,
                                lambda: p.prefetch(QUERY, session_id='b'))
            assert len(result) == 1 and B in result[0] and A not in result[0]
        else:
            reject()
        assert p.diagnostics()['last_recall'] == 'recalled' and m.describe_recall()
        record('request-validation-' + stage + '-' + rejected_session,
               {'observations': observations, 'real_engine_cpu_onnx': True})
    finally:
        m.shutdown_all()


@pytest.mark.parametrize('session_id', ['', 'b'])
def test_default_and_explicit_current_session_recall_are_admitted(tmp_path, session_id):
    p = open_real(tmp_path / 'valid')
    m = manager(p)
    p.on_session_switch('b', gateway_session_key='beta')
    try:
        before = p._request_id
        text = p.prefetch(QUERY, session_id=session_id)
        assert B in text and A not in text
        assert p._request_id == before + 1
        assert p._session_id == 'b' and p.diagnostics()['last_recall'] == 'recalled'
        assert m.describe_recall()
    finally:
        m.shutdown_all()


@pytest.mark.parametrize('state', ['uninitialized', 'unavailable', 'closed'])
def test_not_ready_recall_is_rejected_without_state_mutation(tmp_path, state):
    if state == 'closed':
        p = open_real(tmp_path / state)
        p.shutdown()
    else:
        p = EnhancedCogneeProvider(hermes_home=tmp_path / state)
        if state == 'unavailable':
            p.initialize('a', hermes_home=tmp_path / state)
    assert p.diagnostics()['state'] == state
    m = manager(p)
    try:
        before = snapshot(p, m)
        assert p.prefetch(QUERY) == ''
        assert snapshot(p, m) == before
    finally:
        m.shutdown_all()
