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
sys.path[:0] = [str(REPO / 'integrations/hermes'), str(REPO),
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


def gated_call(p, needle, action, call=None):
    """Gate one provider execution line; always release worker and trace."""
    code = EnhancedCogneeProvider.prefetch.__code__
    source, start = inspect.getsourcelines(EnhancedCogneeProvider.prefetch)
    line = start + next(i for i, text in enumerate(source) if needle in text)
    entered, release = threading.Event(), threading.Event()
    result, errors = [], []
    def trace(frame, event, arg):
        if event == 'line' and frame.f_code is code and frame.f_lineno == line:
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
    assert not worker.is_alive() and not errors, errors
    return result


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
