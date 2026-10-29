"""One offline native text-ingress qualification; reuse the prior transport pass.

Two existing restricted identities exchange only invented text. The receiver
creates a new disposable profile itself; no original profile, key or API is read.
Results and failures are immutable; repeating the command never repeats probes.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import resource
import socket
import subprocess
import tempfile

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
PACKAGE = BASE / 'operator-launch-completion-batch-v2'
ARTIFACT = BASE / 'operator-isolated-native-text-ingress-v1'
TRANSPORT_ARTIFACT = BASE / 'operator-isolated-gateway-transport-v1'
TRANSPORT_QUAL_SHA = '0fc198a6942a5b37ad2535504f6544e3652f41a728e3d3a470eebf8b4e007e57'
PUBLIC = {'isolated_gateway_transport.py': '543a712ebe8ab95bdd9ab48bb202e71be116e5a51ea138236f0a4baa6acf9711', 'isolated_native_text_ingress.py': '579122e02485597535f71fd6f8f40250a6a231e1dd6e99a4bab7f95689fa88a9', 'probe_isolated_native_text_ingress.py': '7afcbc1804bb1eca4d4ff95f244abea615f52074b6f8c4165d478100c84536b3'}
NATIVE = {
    'gateway/run.py': 'a98407aeb888003a2dcb75287291ecc33c8509a24ff8ef6576c00bca4e28de9c',
    'gateway/run_adapters.py': 'd2a6825f72fa5cebc167d073601c660250a0bf884a2321754bee189c5f7fccf9',
    'gateway/run_inbound.py': 'e1148cc822a69802c60c07c03afea08a3661975e6d16d57798673e1e87937d60',
    'gateway/authz_mixin.py': '16178cdab78dd0fa32432bbf65bc1259e3b3da3eab1030c920b3b5a3cf33244d',
    'gateway/session.py': 'ed560fb1b416e1bc111ed9c1e20945238fc2632c60121852a428b4ec02b60d5c',
    'gateway/platforms/event.py': '629770dd61c610bde1a62c6735e2a0ccf04df0399731cc40c40b33d30c8480e8',
    'tools/clarify_gateway.py': '7052ea9832fc93e40146fb1226753fd1bd5618943cf437d822a2821840fba26c',
    'agent/secret_scope.py': 'dce64ce99a6966836108e202e1db41c4be97bd3dad41a79e357f39b8d7e90dec',
}


def require(value):
    if not value:
        raise ValueError('isolated_native_text_qualification_refused')


def definitions(path, digest):
    raw = path.read_bytes()
    require(0 < len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == digest)
    scope = {'__name__':'verified_native_text_support', '__file__':str(path)}
    exec(compile(raw, '<verified-native-text-support>', 'exec'), scope)
    return scope


def prior_pass(read, rows, transport):
    context = json.loads(read(TRANSPORT_ARTIFACT / 'context.private.json', 0))
    require(context.get('source_sha256') == TRANSPORT_QUAL_SHA
        and context.get('transport_sha256') == transport['TRANSPORT_SHA']
        and read(TRANSPORT_ARTIFACT / 'selected-bindings.private.json', 0) == transport['canonical'](rows))
    evidence = Path(context['evidence'])
    require(evidence.parent == BASE / 'operator-evidence' and evidence.name.startswith('isolated-transport-'))
    summary = json.loads(read(evidence / 'summary.json', 0))
    require(summary.get('complete') is True and summary.get('completed_cases') == 3
        and summary.get('distinct_restricted_uids') == 2
        and summary.get('operator_helper_sha256') == TRANSPORT_QUAL_SHA
        and summary.get('source_revision') == BASE.name
        and summary.get('binding_manifest_sha256') == context.get('bindings_sha256')
        and summary.get('binding_manifest_sha256') == hashlib.sha256(transport['canonical'](rows)).hexdigest()
        and summary.get('kernel_authenticated_transport_qualified') is True
        and summary.get('all_admission_policies_preserved_disabled') is True
        and summary.get('fleet_launch_approved') is False)
    return str(evidence)


def receipt(value, role):
    require(role in {'frontend','worker'})
    flags = {'complete','identity_restricted','invented_text_roundtrip','profile_override_absent',
        'network_unused','real_profiles_unread'}
    if role == 'worker':
        flags |= {'native_sender_denial','duplicate_request_denial','native_clarification_preserved_and_resolved'}
    require(isinstance(value, dict) and set(value) == flags | {'role'} and value.get('role') == role
        and all(value.get(name) is True for name in flags))
    return value


def run_case(rows, transport, helper):
    frontend, worker = [pwd.getpwnam(row['user']) for row in rows]
    sockets = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    for connection in sockets:
        connection.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
    source = ("def child():\n import sys\n sys.path.insert(0," + repr(str(ARTIFACT)) + ")\n"
        " from probe_isolated_native_text_ingress import main\n raise SystemExit(main())\n").encode()
    processes = []
    try:
        for role, account, connection in [('worker',worker,sockets[1]),('frontend',frontend,sockets[0])]:
            packet = dict(uid=account.pw_uid, gid=account.pw_gid, role=role, fd=connection.fileno(),
                frontend_uid=frontend.pw_uid, worker_uid=worker.pw_uid, profile_id=rows[1]['user'][6:])
            processes.append((role, transport['spawn'](account, packet, helper, source)))
        for connection in sockets:
            connection.close()
        reports = []
        for role, process in processes:
            status = process.wait(timeout=145)
            raw = process.stdout.read(4097)
            require(len(raw) <= 4096)
            try:
                value = json.loads(raw)
            except (ValueError, UnicodeError):
                value = None
            if status != 0 or not isinstance(value, dict) or value.get('complete') is not True:
                error = ValueError('native_text_child_incomplete')
                diagnostic = dict(role=role, exit_code=status, phase='startup', error_kind='other')
                if isinstance(value, dict):
                    if isinstance(value.get('phase'), str) and value['phase'] in {'identity','socket_identity','native_imports','native_receive',
                            'native_dispatch','preservation','frontend_exchange'}:
                        diagnostic['phase'] = value['phase']
                    if isinstance(value.get('error_kind'), str) and value['error_kind'] in {'ValueError','PermissionError','NativeIngressError',
                            'TransportError','AttributeError','TypeError'}:
                        diagnostic['error_kind'] = value['error_kind']
                    counts = value.get('denied_attempt_counts')
                    if isinstance(counts, dict) and set(counts) == {'network','real_profile','subprocess'} and all(
                            type(number) is int and 0 <= number <= 4096 for number in counts.values()):
                        diagnostic['denied_attempt_counts'] = counts
                error.child_diagnostic = diagnostic
                raise error
            reports.append(receipt(value, role))
        return reports
    finally:
        for connection in sockets:
            connection.close()
        for _, process in processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait(timeout=3)
            for stream in (process.stdin, process.stdout):
                if stream:
                    stream.close()


def main():
    require(os.geteuid() == 0)
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE, (0,0))
    directory = Path(__file__).parent
    transport = definitions(directory / 'qualify_isolated_gateway_transport.py', TRANSPORT_QUAL_SHA)
    support = definitions(PACKAGE / 'recover_launch_graph_operator.py', transport['SUPPORT_SHA'])
    read, write, canonical = support['read_file'], support['private_write'], transport['canonical']
    source = globals()['_verified_source_bytes']
    digest = hashlib.sha256(source).hexdigest()
    require(set(PUBLIC) == {'isolated_gateway_transport.py','isolated_native_text_ingress.py','probe_isolated_native_text_ingress.py'})
    if os.path.lexists(ARTIFACT / 'context.private.json'):
        context = json.loads(read(ARTIFACT / 'context.private.json', 0))
        require(context.get('source_sha256') == digest and context.get('component_hashes') == PUBLIC)
        require(context.get('native_source_hashes') == NATIVE
            and hashlib.sha256(read(ARTIFACT / 'qualify_isolated_native_text_ingress.py',0)).hexdigest() == digest)
        for name, expected in PUBLIC.items():
            require(hashlib.sha256((ARTIFACT / name).read_bytes()).hexdigest() == expected)
        require(hashlib.sha256(read(ARTIFACT / 'selected-bindings.private.json',0)).hexdigest() == context.get('bindings_sha256'))
        evidence = Path(context['evidence'])
        require(evidence.parent == BASE / 'operator-evidence' and evidence.name.startswith('isolated-native-text-'))
        result = json.loads(read(evidence / 'summary.json', 0))
        require(result.get('operator_helper_sha256') == digest and result.get('source_revision') == BASE.name
            and result.get('binding_manifest_sha256') == context.get('bindings_sha256'))
        print(json.dumps(result), flush=True)
        return 0 if result.get('complete') is True else 1
    policy = definitions(PACKAGE / 'fleet_credential_policy.py', transport['POLICY_SHA'])
    rows = transport['admission'](read, policy)
    previous = prior_pass(read, rows, transport)
    protected = definitions(PACKAGE / 'renew_fleet_credentials.py',
        '146f340ad9258179bf3555f8949ce08ba66aff5554264537603244018d4e7495')['protected']
    executable = Path(transport['EXECUTABLE'])
    protected(executable, final_link=True); protected(executable.resolve(strict=True))
    protected(Path('/usr/bin/setpriv'))
    native = executable.parent.parent.parent / 'repo'
    for name, expected in NATIVE.items():
        path = native / name
        protected(path)
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected)
    components = {name:(directory / name).read_bytes() for name in PUBLIC}
    require(all(hashlib.sha256(raw).hexdigest() == PUBLIC[name] for name,raw in components.items()))
    require(not os.path.lexists(ARTIFACT))
    ARTIFACT.mkdir(mode=0o755)
    ARTIFACT.chmod(0o755)  # Public code must remain traversable under umask 077.
    write(ARTIFACT / 'qualify_isolated_native_text_ingress.py', source)
    for name, raw in components.items():
        write(ARTIFACT / name, raw); (ARTIFACT / name).chmod(0o644)
    bindings = canonical(rows)
    write(ARTIFACT / 'selected-bindings.private.json', bindings)
    evidence = Path(tempfile.mkdtemp(prefix='isolated-native-text-', dir=BASE / 'operator-evidence'))
    context = dict(source_sha256=digest, component_hashes=PUBLIC, native_source_hashes=NATIVE,
        bindings_sha256=hashlib.sha256(bindings).hexdigest(), evidence=str(evidence))
    write(ARTIFACT / 'context.private.json', canonical(context))
    helper = definitions(PACKAGE / 'qualify_launch_isolated_accounts.py', transport['HELPER_SHA'])
    before = read(BASE / 'operator-named-fleet-issuer-review-v1/candidate-policy.json',0)
    result = dict(complete=False, source_revision=BASE.name, evidence=str(evidence), operator_helper_sha256=digest,
        component_hashes=PUBLIC, native_source_hashes=NATIVE, binding_manifest_sha256=context['bindings_sha256'],
        reused_transport_evidence=previous, qualification_surface='invented_dm_text_native_handler_with_distinct_uids',
        automatic_retry=False,
        credentials_issued=0, keys_read=False, source_profiles_changed=False, real_profile_contents_read=False,
        services_installed=False, platform_adapters_started=0, model_called=False, memory_api_called=False,
        canonical_memory_edits=False, production_dispatch_qualified=False, actual_profile_admission_qualified=False,
        native_gateway_integration_qualified=False, fleet_launch_approved=False)
    try:
        write(evidence / 'probe.started.json', canonical(dict(started=True)))
        reports = run_case(rows, transport, helper)
        write(evidence / 'owner-receipts.json', canonical(reports))
        require(read(BASE / 'operator-named-fleet-issuer-review-v1/candidate-policy.json',0) == before)
        result.update(complete=True, native_dm_text_ingress_component_qualified=True,
            native_authorization_and_pending_clarification_preserved=True, distinct_restricted_uids=2,
            all_admission_policies_preserved_disabled=True)
    except (Exception, KeyboardInterrupt) as error:
        result.update(category='native_text_ingress_incomplete_preserve_evidence_no_automatic_retry',
            error_kind=type(error).__name__ if type(error).__name__ in
                {'ValueError','PermissionError','TimeoutExpired','KeyboardInterrupt'} else 'other')
        if isinstance(getattr(error,'child_diagnostic',None),dict):
            result['child_diagnostic'] = error.child_diagnostic
    write(evidence / 'summary.json', canonical(result))
    print(json.dumps(result), flush=True)
    return 0 if result['complete'] else 1
