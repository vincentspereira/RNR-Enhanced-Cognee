"""Synthetic timing tests: default CPU ONNX/LanceDB unless labelled unit.

Trace gates control scheduling only. Host config loader is stubbed; no activation.
"""
import inspect
import json
import os
from pathlib import Path
import shutil
import sys
import threading
import time
import types
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO / 'integrations/hermes-chat-switch-safety-v1'), str(REPO),
                 '/home/vincentspereira/agent-workspace/hermes-agent']
from enhanced_cognee_hermes import EnhancedCogneeProvider

QUERY = 'What notebooks are in the synthetic Helios archive?'
A = 'Synthetic Helios archive A stores turquoise notebooks.'
B = 'Synthetic Helios archive B stores copper notebooks.'


def record(name, data):
    if os.environ.get('CHAT_SAFETY_OUT'):
        with (Path(os.environ['CHAT_SAFETY_OUT']) / (name + '.json')).open('x') as f:
            json.dump(data, f, indent=2)


def open_real(home):
    from src.hermes_memory.runtime import EnhancedMemoryEngine
    from src.hermes_memory.embeddings import LocalOnnxEmbedder
    p = EnhancedCogneeProvider(hermes_home=home)
    p.save_config({'auto_capture': True}, str(home))
    shutil.copytree(REPO / '.data/hermes-models/bge-small-en-v1.5',
                    home / 'enhanced-cognee/models/bge-small-en-v1.5')
    p.initialize('a', hermes_home=home, platform='telegram', gateway_session_key='alpha')
    assert isinstance(p._backend, EnhancedMemoryEngine)
    assert isinstance(p._backend.embedder, LocalOnnxEmbedder)
    assert p._backend.embedder._session.get_providers() == ['CPUExecutionProvider']
    p.sync_turn(A, '', turn_author={'id': 'alice'})
    p.on_session_switch('b', gateway_session_key='beta')
    p.sync_turn(B, '', turn_author={'id': 'bob'})
    assert B in p.prefetch(QUERY) and A not in p.prefetch(QUERY)
    p.on_session_switch('a', gateway_session_key='alpha')
    assert A in p.prefetch(QUERY)
    return p


def manager(p):
    from hermes_constants import set_hermes_home_override, reset_hermes_home_override
    token = set_hermes_home_override(p._home)
    config = types.ModuleType('hermes_cli.config')
    config.load_config = lambda: {}
    try:
        with patch.dict(sys.modules, {'hermes_cli.config': config}):
            from agent.memory_manager import MemoryManager
            m = MemoryManager()
            m.add_provider(p)
    finally:
        reset_hermes_home_override(token)
    return m


def gated_call(p, needle, action, call=None, method='prefetch'):
    """Gate one provider execution line; always release worker and trace."""
    function = getattr(EnhancedCogneeProvider, method)
    code = function.__code__
    source, start = inspect.getsourcelines(function)
    line = start + next(i for i, text in enumerate(source) if needle in text)
    entered, release = threading.Event(), threading.Event()
    result, errors = [], []
    def trace(frame, event, arg):
        if (event == 'line' and frame.f_code is code and frame.f_lineno == line
                and not entered.is_set()):
            entered.set()
            if not release.wait(4):
                raise RuntimeError('timing gate not released')
        return trace
    def run():
        try:
            sys.settrace(trace)
            result.append((call or (lambda: p.prefetch(QUERY)))())
        except Exception as exc:
            errors.append(repr(exc))
        finally:
            sys.settrace(None)
    oldtrace = threading.gettrace()
    threading.settrace(trace)
    worker = threading.Thread(target=run)
    worker.start()
    try:
        assert entered.wait(3)
        action()
    finally:
        release.set()
        worker.join(6)
        threading.settrace(oldtrace)
    assert not worker.is_alive() and not errors, errors
    return result


@pytest.mark.parametrize('branch', ['trivial', 'empty', 'exception', 'deadline'])
def test_old_completion_cannot_clobber_new_chat_indicator(tmp_path, branch):
    """Real engine; exceptional input is a boundary unit stimulus, not a backend mock."""
    p = open_real(tmp_path / branch)
    assert p._backend is not None
    m = manager(p)
    query, needle = QUERY, 'if not entries:'
    if branch == 'trivial':
        query, needle = 'hello', 'if is_trivial_prompt(query):'
    elif branch == 'exception':
        class BrokenQuery(str):
            def __str__(self):
                raise ValueError('synthetic input conversion error')
        query, needle = BrokenQuery(QUERY), 'started = time.monotonic()'
    elif branch == 'deadline':
        class SlowQuery(str):
            def __str__(self):
                time.sleep(2.1)  # Scheduling-only delay; actual model/engine unchanged.
                return super().__str__()
        query, needle = SlowQuery(QUERY), 'if elapsed > 2.0:'
    else:
        for row in p._backend.search(QUERY, p._sessions['a']['scope'], min_score=.25):
            p._backend.withdraw(row['source_id'], p._sessions['a']['scope'])
        assert p._backend.search(QUERY, p._sessions['a']['scope']) == []
    newer = []
    def switch_and_recall():
        m.on_session_switch('b', gateway_session_key='beta')
        newer.append(m.prefetch_all(QUERY, session_id='b'))
        assert B in newer[-1] and A not in newer[-1]
    try:
        result = gated_call(p, needle, switch_and_recall, lambda: p.prefetch(query))
        status = p.diagnostics()
        record('old-branch-' + branch, {'result': result, 'newer': newer,
                                       'status': status, 'indicator': m.describe_recall()})
        assert result == ['']
        assert status['last_recall'] == 'recalled' and m.describe_recall()
    finally:
        m.shutdown_all()



def test_real_stalled_lookup_switch_busy_shutdown_is_nonblocking(tmp_path):
    import fcntl
    from agent.memory_provider import spawn_context_thread
    p = open_real(tmp_path / 'stalled')
    assert p._home is not None
    m = manager(p)
    fd = os.open(p._home / 'enhanced-cognee/writer.lock', os.O_RDWR)
    fcntl.flock(fd, fcntl.LOCK_EX)
    result, errors = [], []
    def lookup():
        try:
            result.append(m.prefetch_all(QUERY, session_id='a'))
        except Exception as exc:
            errors.append(repr(exc))
    worker = spawn_context_thread(lookup, name='synthetic-stalled-lookup')
    worker.start()
    try:
        deadline = time.monotonic() + 3
        while not p._backend_lock.locked() and time.monotonic() < deadline:
            time.sleep(.001)
        assert p._backend_lock.locked()
        start = time.monotonic()
        m.on_session_switch('b', gateway_session_key='beta')
        switch_elapsed = time.monotonic() - start
        assert switch_elapsed < .5 and p._session_id == 'b'
        assert p.prefetch(QUERY, session_id='b') == ''
        assert p.diagnostics()['last_recall'] == 'busy'
        start = time.monotonic()
        p.shutdown()
        shutdown_elapsed = time.monotonic() - start
        assert shutdown_elapsed < .5
        assert p.diagnostics()['close_pending'] and p._backend is not None
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        worker.join(6)
    try:
        assert not worker.is_alive() and not errors
        assert result == [''] and m.describe_recall() == ''
        assert p._backend is None and not p.diagnostics()['close_pending']
        assert p.prefetch(QUERY) == ''
        status = p.diagnostics()
        record('stalled-shutdown', {'result': result, 'status': status,
                                   'switch_elapsed': switch_elapsed,
                                   'shutdown_elapsed': shutdown_elapsed})
        assert status['state'] == 'closed' and status['last_recall'] == 'closed'
    finally:
        m.shutdown_all()


def test_real_shutdown_at_backend_lock_handoff_does_not_leak(tmp_path):
    p = open_real(tmp_path / 'handoff')
    closer, errors = [], []
    begun, done = threading.Event(), threading.Event()
    def close():
        begun.set()
        try:
            p.shutdown()
        except Exception as exc:
            errors.append(repr(exc))
        finally:
            done.set()
    def start_shutdown():
        worker = threading.Thread(target=close)
        closer.append(worker)
        worker.start()
        assert begun.wait(2)
        done.wait(.1)  # Let shutdown contend; release gate even if state lock is held.
    try:
        result = gated_call(p, 'self._backend_lock.release()', start_shutdown,
                            method='_backend_call')
        closer[0].join(4)
        status = p.diagnostics()
        record('shutdown-handoff', {'result': result, 'status': status})
        assert not closer[0].is_alive() and not errors
        assert p._backend is None and not status['close_pending']
        assert status['state'] == 'closed' and p.recall_status() is None
    finally:
        for worker in closer:
            worker.join(4)
        p.shutdown()


def test_real_superseding_request_at_publication_preserves_latest(tmp_path):
    p = open_real(tmp_path / 'superseding-publication')
    m = manager(p)
    newer = []
    def latest():
        newer.append(p.prefetch('Which turquoise notebooks does Helios archive A store?', session_id='a'))
        assert A in newer[-1]
    try:
        result = gated_call(p, 'RecallStatus("Enhanced Cognee", len(entries))', latest,
                            lambda: m.prefetch_all(QUERY, session_id='a'))
        status = p.diagnostics()
        record('superseding-publication', {'result': result, 'newer': newer,
                                          'status': status, 'indicator': m.describe_recall()})
        assert result == [''] and status['last_recall'] == 'recalled'
        recall = p.recall_status()
        assert m.describe_recall() and recall is not None and recall.count == 1
    finally:
        m.shutdown_all()


def test_real_busy_superseding_request_keeps_busy_after_old_return(tmp_path):
    import fcntl
    from agent.memory_provider import spawn_context_thread
    p = open_real(tmp_path / 'busy')
    assert p._home is not None
    fd = os.open(p._home / 'enhanced-cognee/writer.lock', os.O_RDWR)
    fcntl.flock(fd, fcntl.LOCK_EX)
    result, errors = [], []
    def old():
        try:
            result.append(p.prefetch(QUERY))
        except Exception as exc:
            errors.append(repr(exc))
    worker = spawn_context_thread(old, name='synthetic-busy-old')
    worker.start()
    try:
        deadline = time.monotonic() + 3
        while not p._backend_lock.locked() and time.monotonic() < deadline:
            time.sleep(.001)
        assert p._backend_lock.locked()
        assert p.prefetch(QUERY) == '' and p.diagnostics()['last_recall'] == 'busy'
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        worker.join(6)
    try:
        status = p.diagnostics()
        record('superseding-busy', {'result': result, 'status': status})
        assert not worker.is_alive() and not errors and result == ['']
        assert status['last_recall'] == 'busy' and p.recall_status() is None
        assert A in p.prefetch(QUERY)
    finally:
        p.shutdown()


def test_real_coherent_admission_discards_old_chat(tmp_path):
    p = open_real(tmp_path / 'admission')
    m = manager(p)
    try:
        result = gated_call(p, 'if is_trivial_prompt(query):',
                            lambda: m.on_session_switch('b', gateway_session_key='beta'),
                            lambda: m.prefetch_all(QUERY, session_id='a'))
        indicator = m.describe_recall()
        current = m.prefetch_all(QUERY, session_id='b')
        record('coherent-admission', {'result': result, 'indicator': indicator,
                                     'current': current, 'real_cpu_onnx_lancedb': True})
        assert result == [''] and indicator == ''
        assert B in current and A not in current
        assert m.describe_recall()
    finally:
        m.shutdown_all()


def test_real_switch_at_publication_discards_old_result(tmp_path):
    p = open_real(tmp_path / 'publication')
    m = manager(p)
    try:
        result = gated_call(p, 'RecallStatus("Enhanced Cognee", len(entries))',
                            lambda: m.on_session_switch('b', gateway_session_key='beta'),
                            lambda: m.prefetch_all(QUERY, session_id='a'))
        indicator = m.describe_recall()
        record('publication-switch', {'result': result, 'indicator': indicator})
        assert result == [''] and indicator == ''
        assert B in m.prefetch_all(QUERY, session_id='b')
    finally:
        m.shutdown_all()

