"""Read-only owner preflight diagnosis; no credentials issued or connections."""
from pathlib import Path
import hashlib
import json
import os
import pwd
import subprocess
import sys
import uuid


PREPARATION_SHA = 'a21eec3cef6bd37c71467f0c867aaf392700519de2e24aacf837c8fe07d2a175'
OWNER_SOURCE = r'''
def child(packet):
    result = dict(complete=False, phase='identity', profiles_changed=False,
        credentials_issued=0, store_connections=False)
    try:
        account = pwd.getpwuid(os.geteuid())
        require(account.pw_uid == packet['uid'] and account.pw_uid != 0
            and account.pw_dir == packet['home'] and not os.getgroups())
        old = Path(packet['candidate'])
        require(old.parent == Path(account.pw_dir))
        core = definitions(packet['issuer_source'].encode(), ISSUER_SHA)
        result['phase'] = 'placeholder'
        placeholder = Path(account.pw_dir) / '.hermes'
        require(stat.S_ISDIR(placeholder.lstat().st_mode)
            and placeholder.stat().st_uid == account.pw_uid
            and stat.S_IMODE(placeholder.stat().st_mode) == 0o700
            and set(os.listdir(placeholder)) == {'.isolation-marker'}
            and (placeholder / '.isolation-marker').read_bytes() == b'invented-isolation-marker-v1')
        result['phase'] = 'existing_provider_config'
        require(not os.path.lexists(old / 'enhanced_cognee.json')
            and not os.path.lexists(old / 'plugins/enhanced_cognee'))
        result['phase'] = 'directory_open'
        directory = core['open_directory'](old, {0, account.pw_uid})
        try:
            result['phase'] = 'environment_read'
            env = core['read_private_at'](directory, '.env', account.pw_uid)[0]
            result['phase'] = 'configuration_read'
            config = core['read_private_at'](directory, 'config.yaml', account.pw_uid)[0]
        finally:
            os.close(directory)
        result['phase'] = 'configuration_shape'
        import yaml
        provider_settings(yaml.safe_load(config))
        result['phase'] = 'environment_shape'
        # Public dummy string, never published or sent to any API.
        core['prepare_environment'](env, 'unpublished-diagnostic-placeholder')
        result['phase'] = 'auth_read'
        if (old / 'auth.json').exists():
            (old / 'auth.json').read_bytes()
        result.update(complete=True, phase='complete')
    except Exception as error:
        result['error_kind'] = type(error).__name__ if type(error).__name__ in {
            'PermissionError', 'FileNotFoundError', 'ValueError', 'ProvisionError',
            'ModuleNotFoundError', 'OSError'} else 'other'
        if isinstance(error, OSError) and type(error.errno) is int:
            result['errno'] = error.errno
    return result
'''


def main():
    if os.geteuid() != 0 or len(sys.argv) != 1:
        raise ValueError('fixed_root_operator_required')
    os.umask(0o077)
    directory = Path(__file__).parent
    raw = (directory / 'prepare_launch_candidate_provider.py').read_bytes()
    if hashlib.sha256(raw).hexdigest() != PREPARATION_SHA:
        raise ValueError('reviewed_preparation_required')
    core = {'__name__': 'verified_preparation'}
    exec(compile(raw, '<verified-preparation>', 'exec'), core)
    shared = core['definitions']((directory / 'recover_launch_graph_operator.py').read_bytes(),
        'd7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef')
    read = shared['read_file']
    prior = json.loads(read(core['BASE'] / 'operator-evidence/candidate-provider-3ffd_uk3/summary.json', 0))
    if not (prior.get('candidate_modified') is False and prior.get('ordinary_credential_published') is False
            and prior.get('owner_failure_phase') == 'preflight'):
        raise ValueError('unmodified_retained_failure_required')
    paths = list(core['STAGE'].glob('*.candidate.private.json'))
    if len(paths) != 1:
        raise ValueError('unique_staged_candidate_required')
    staged = json.loads(read(paths[0], 0))
    account = pwd.getpwnam(staged['user'])
    if account.pw_uid != staged['uid'] or account.pw_uid == 0:
        raise ValueError('fixed_owner_required')
    issuer = (directory / 'provision_pilot_access.py').read_bytes()
    core['definitions'](issuer, core['ISSUER_SHA'])
    helper = core['definitions']((directory / 'qualify_launch_isolated_accounts.py').read_bytes(),
        'd0425ae9f2598e79a732e41f23ebbc09bcfd77993b91c8cddb4e45fa192e2a94')
    code, line = helper['owner_program'](raw + OWNER_SOURCE.encode())
    packet = dict(uid=account.pw_uid, home=account.pw_dir, candidate=staged['candidate'], issuer_source=issuer.decode())
    process = subprocess.run(['/usr/bin/setpriv', '--no-new-privs', '--', helper['EXECUTABLE'],
        '-I', '-B', '-c', core['owner_launcher'](code)],
        input=line + json.dumps(packet).encode() + b'\n', stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, timeout=30, cwd='/', user=account.pw_uid,
        group=account.pw_gid, extra_groups=(),
        env={'PATH': '/usr/bin:/bin', 'HOME': account.pw_dir, 'PYTHONDONTWRITEBYTECODE': '1'})
    if process.returncode != 0 or not 0 < len(process.stdout) <= 2048:
        raise ValueError('bounded_diagnostic_receipt_required')
    result = json.loads(process.stdout)
    allowed = {'complete', 'phase', 'profiles_changed', 'credentials_issued', 'store_connections', 'error_kind', 'errno'}
    if set(result) - allowed or result.get('profiles_changed') is not False or result.get('credentials_issued') != 0:
        raise ValueError('fixed_diagnostic_receipt_required')
    result.update(stage='retained_candidate_preflight_inspection', fleet_launch_approved=False)
    path = core['BASE'] / 'operator-evidence' / ('candidate-preflight-inspection-' + uuid.uuid4().hex + '.json')
    result['evidence'] = str(path)
    shared['private_write'](path, json.dumps(result).encode())
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('{"complete":false,"category":"candidate_inspection_refused_no_secret_output"}')
        raise SystemExit(1)
