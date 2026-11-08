"""Explicit continuation of the preserved main endpoint preflight refusal.

Freeze a NEW package and NEW finite jobs. The original batch/source/evidence
stay unchanged. Qualification still requires implementation recovery to pass;
no completed probe, model turn or production launch is repeated.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import resource
import sys

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
PREVIOUS = BASE / 'operator-launch-completion-batch-v1'
ARTIFACT = BASE / 'operator-launch-completion-batch-v2'
PRIOR_EVIDENCE = BASE / 'operator-evidence/launch-implementation-ryrn0iw5'
DRIVER_SHA = 'd99a819e0c64a5e0d60632f15c8ff3fb57cbf294c4ed33865605702b5796becc'
OWNER_SHA = '9877ad30ad2047dc29f582d844e28d6d33b7e28ab06b0b06ac8b49d698a4ba82'


def require(value):
    if not value:
        raise ValueError('explicit_completion_continuation_refused')


def previous_attempt(scope):
    support = scope['definitions'](PREVIOUS / 'recover_launch_graph_operator.py', scope['SUPPORT_SHA'])
    read = support['read_file']
    context = json.loads(read(PREVIOUS / 'implementation-context.json', 0))
    require(context == {'evidence': str(PRIOR_EVIDENCE)})
    result = json.loads(read(PRIOR_EVIDENCE / 'finish.summary.json', 0))
    require(result.get('complete') is False and result.get('phase') == 'implementation'
            and result.get('operator_helper_sha256') == DRIVER_SHA
            and result.get('source_revision') == BASE.name and result.get('evidence') == str(PRIOR_EVIDENCE)
            and result.get('operator_job_stopped') is True and result.get('credentials_issued') == 2
            and result.get('owner_diagnostic') == {'error_kind': 'ValueError', 'phase': 'main_configuration_preflight'}
            and result.get('all_admission_policies_preserved_disabled') is True
            and all(result.get(key) is False for key in ('canonical_memory_edits', 'source_profiles_changed',
                'existing_launchers_changed', 'chat_model_called', 'fleet_launch_approved')))
    require(not any(os.path.lexists(PRIOR_EVIDENCE / name) for name in
            ('main-configuration.receipt.json', 'main-generation.started.json', 'main-restored.private.json')))
    require(scope['stopped'](scope['metadata']('ec-launch-completion-implementation-20261027.service')))
    require(not os.path.lexists(PREVIOUS / 'qualification-context.json'))


def adapt(scope, source, filename):
    original_definitions = scope['definitions']
    directory = Path(filename).parent
    def definitions(path, digest):
        if (path.name == 'launch_completion_owner.py' and path.parent == directory
                and directory != ARTIFACT and digest == OWNER_SHA):
            path = directory / 'launch_completion_owner_v2.py'
        return original_definitions(path, digest)
    scope.update(ARTIFACT=ARTIFACT, OWNER_SHA=OWNER_SHA,
        PINS=dict(scope['PINS'], **{'launch_completion_owner.py': OWNER_SHA}),
        PHASES=scope['PHASES'] | {'main_environment_preflight', 'main_placeholder_preflight'},
        definitions=definitions, __file__=str(filename), _verified_source_bytes=source)
    def units(mode):
        require(mode in {'implementation', 'qualification'})
        return 'ec-launch-completion-' + mode + '-v2-20261027'
    scope['units'] = units
    return scope


def verified_driver():
    require(os.geteuid() == 0)
    raw = (PREVIOUS / 'launch_completion_batch.py').read_bytes()
    require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == DRIVER_SHA)
    scope = {'__name__': 'verified_previous_completion_driver'}
    exec(compile(raw, '<verified-previous-completion-driver>', 'exec'), scope)
    source = globals().get('_verified_source_bytes', Path(__file__).read_bytes())
    return adapt(scope, source, __file__)


def launch(mode):
    require(mode in {'implementation', 'qualification'})
    scope = verified_driver()
    # Existing jobs only reattach/return retained evidence through the original
    # controller. The explicit continuation is admitted once, never auto-retried.
    if not os.path.lexists(ARTIFACT / (mode + '-context.json')):
        previous_attempt(scope)
    return scope['launch'](mode)


if __name__ == '__main__':
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    try:
        require(len(sys.argv) == 3 and sys.argv[1] == '--worker' and sys.argv[2] in {'implementation', 'qualification'})
        raise SystemExit(verified_driver()['worker'](sys.argv[2]))
    except Exception:
        print('{"complete":false,"category":"explicit_completion_continuation_refused_no_secret_output"}', flush=True)
        raise SystemExit(1)
