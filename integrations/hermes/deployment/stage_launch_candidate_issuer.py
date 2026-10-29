"""Stage a separate disabled issuer for the isolated candidate, no activation.

Preserve the existing fleet policy/packages. Carry the tested traversal fix into
new public issuer sources; no credentials, keys or profile files are read/written.
"""
from __future__ import annotations
import ast
import hashlib
import json
import os
from pathlib import Path
import pwd
import subprocess
import sys

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
PACKAGE = BASE / 'operator-isolated-issuer-candidate-v3'
CANDIDATE = BASE / 'operator-evidence/candidate-provider-f8uifc8j'
BACKUP = BASE / 'operator-evidence/candidate-profile-backup-tjfy2101'
NATIVE = BASE / 'operator-evidence/candidate-native-unit-s317r31u'
CORE_SHA = 'f2bf3ec50bfd8414011aa322e027f7c266a7102d558c0b7d0518549e8a8b2cc6'
DRIVER_SHA = 'a7432a8a6c258b2f81466f51b782dd9b53c2211a5a52fcb863f3a1567ad858bf'
FIX_SHA = 'e54da1d75c89677fe01cd173c965367e2b5ca47fbb7a2cbff4d9ed766d13fc67'


def require(value):
    if not value:
        raise ValueError('isolated_issuer_staging_refused')


def checked(directory, name, digest):
    raw = (directory / name).read_bytes()
    require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == digest)
    return raw


def definitions(raw):
    value = {'__name__': 'verified_isolated_issuer_stage'}
    exec(compile(raw, '<verified-public-support>', 'exec'), value)
    return value


def build_sources(core, driver, fix):
    require(hashlib.sha256(core).hexdigest() == CORE_SHA
        and hashlib.sha256(driver).hexdigest() == DRIVER_SHA and hashlib.sha256(fix).hexdigest() == FIX_SHA)
    tree = ast.parse(fix)
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'open_candidate_directory']
    require(len(functions) == 1)
    patched = ast.get_source_segment(fix.decode(), functions[0])
    patched = patched.replace('def open_candidate_directory(', 'def open_directory(', 1)
    # The issuer's own exception contract, without weakening any tested guard.
    patched = patched.replace('    require(', '    _directory_require(')
    patched = patched.replace("            require(", "            _directory_require(")
    patched = patched.replace("raise ValueError('candidate_directory_identity_changed')", "raise ProvisionError('Directory identity changed.')")
    appendix = "\n\ndef _directory_require(value):\n    if not value:\n        raise ProvisionError('Directory protection refused.')\n\n" + patched + '\n'
    # Insert before main dispatch so operator and owner both use the same fix.
    text = core.decode()
    marker = '\nif __name__ == "__main__":'
    require(text.count(marker) == 1)
    new_core = text.replace(marker, appendix + marker).encode()
    new_driver = driver.decode()
    require(new_driver.count(CORE_SHA) == 1)
    new_driver = new_driver.replace(CORE_SHA, hashlib.sha256(new_core).hexdigest())
    old_policy = 'POLICY = Path("/etc/enhanced-cognee/fleet-credentials.json")'
    old_ledger = 'LEDGER = Path("/var/lib/enhanced-cognee-renewal")'
    require(new_driver.count(old_policy) == 1 and new_driver.count(old_ledger) == 1)
    new_driver = new_driver.replace(old_policy, 'POLICY = Path(' + repr(str(PACKAGE / 'candidate-policy.json')) + ')')
    new_driver = new_driver.replace(old_ledger, 'LEDGER = Path(' + repr(str(PACKAGE / 'root-ledger')) + ')').encode()
    for raw in (new_core, new_driver):
        require(raw.isascii() and len(raw) <= 65536)
        compile(raw, '<isolated-issuer-public-source>', 'exec')
    return new_core, new_driver


def policy_entry(binding, account, policy):
    require(binding['uid'] == account.pw_uid and account.pw_uid != 0
        and binding['user'] == account.pw_name and binding['profile'] == str(Path(account.pw_dir) / '.hermes'))
    scope = binding['scope']
    require(scope['roles'] == ['api_client'] and scope['capture_policy'] == 'selected')
    return dict(name='candidate_' + binding['profile_id'], user=account.pw_name, uid=account.pw_uid,
        home=account.pw_dir, profile=binding['profile'], tenant=scope['tenant'], project_id=scope['project_id'],
        subject=scope['sub'], agent_id=scope['agent_id'], roles=['api_client'], lifetime_seconds=86400,
        origin=policy['ORIGIN'], executable=policy['EXECUTABLE'], enabled=False, reload_qualified=False,
        launch_binding_qualified=False, backup_qualified=True, os_boundary_qualified=True)


def main():
    require(os.geteuid() == 0 and len(sys.argv) == 1)
    os.umask(0o077)
    directory = Path(__file__).parent
    shared = definitions(checked(directory, 'recover_launch_graph_operator.py',
        'd7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef'))
    read, write = shared['read_file'], shared['private_write']
    for path, flag, digest in ((CANDIDATE, 'candidate_provider_api_qualified', FIX_SHA),
        (BACKUP, 'post_configuration_backup_qualified', 'cf10aba63a529bdfffa392fdce2cbc68860133626b1871831e9f60238ab5326c'),
        (NATIVE, 'candidate_headless_native_unit_qualified', 'f085298baabc75b801ff82a79fcde97244a129b87146c87c48f72c5f7da0acd0')):
        receipt = json.loads(read(path / 'summary.json', 0))
        require(receipt.get('complete') is True and receipt.get(flag) is True and receipt.get('operator_helper_sha256') == digest)
    native = json.loads(read(NATIVE / 'summary.json', 0))
    require(native.get('transient_units_stopped') is True)
    binding = json.loads(read(CANDIDATE / 'binding.private.json', 0))
    account = pwd.getpwnam(binding['user'])
    require(os.getgrouplist(account.pw_name, account.pw_gid) == [account.pw_gid])
    boundary = BASE / 'operator-evidence/isolated-accounts-2eq6h4nn'
    boundary_pass = json.loads(read(boundary / 'summary.json', 0))
    accounts = json.loads(read(boundary / 'accounts.private.json', 0))
    require(boundary_pass.get('complete') is True and boundary_pass.get('invented_os_boundary_qualified') is True
        and len([row for row in accounts if row['user'] == account.pw_name
            and row['uid'] == account.pw_uid and row['home'] == account.pw_dir]) == 1)
    core, driver = build_sources(checked(directory, 'provision_pilot_access.py', CORE_SHA),
        checked(directory, 'renew_fleet_credentials.py', DRIVER_SHA),
        checked(directory, 'prepare_launch_candidate_provider_v2.py', FIX_SHA))
    source_map = definitions(driver)['SOURCES']
    sources = {'provision_pilot_access.py': core, 'renew_fleet_credentials.py': driver}
    for name, digest in source_map.items():
        if name != 'provision_pilot_access.py':
            sources[name] = checked(directory, name, digest)
    policy = definitions(sources['fleet_credential_policy.py'])
    staged_policy = policy['validate'](dict(schema=1, profiles=[policy_entry(binding, account, policy)]))
    original_policy = read(Path('/etc/enhanced-cognee/fleet-credentials.json'), 0)
    require(all(row['enabled'] is False for row in policy['validate'](json.loads(original_policy))['profiles']))
    PACKAGE.mkdir(mode=0o755)
    PACKAGE.chmod(0o755)
    hashes = {}
    for name, raw in sources.items():
        write(PACKAGE / name, raw)
        (PACKAGE / name).chmod(0o644)
        hashes[name] = hashlib.sha256(raw).hexdigest()
    write(PACKAGE / 'candidate-policy.json', json.dumps(staged_policy).encode())
    require(read(Path('/etc/enhanced-cognee/fleet-credentials.json'), 0) == original_policy)
    process = subprocess.run(['/usr/bin/python3', '-I', '-B', str(PACKAGE / 'renew_fleet_credentials.py')],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=20, cwd='/',
        env={'PATH': '/usr/bin:/bin', 'HOME': '/', 'PYTHONDONTWRITEBYTECODE': '1'})
    require(process.returncode == 0 and 0 < len(process.stdout) <= 2048)
    receipt = json.loads(process.stdout)
    require(receipt.get('complete') is True and receipt.get('enabled_profiles') == 0 and receipt.get('credentials_published') == 0)
    result = dict(complete=True, source_revision=BASE.name, issuer_candidate=str(PACKAGE),
        operator_helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        disabled_candidate_policy_verified=True, public_component_hashes=hashes,
        credentials_issued=0, keys_read=False, profiles_changed=False, existing_fleet_policy_changed=False,
        timer_enabled=False, installed_issuer_qualified=False, scheduled_renewal_qualified=False,
        actual_profile_admission_qualified=False, fleet_launch_approved=False)
    write(PACKAGE / 'staging.summary.json', json.dumps(result).encode())
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('{"complete":false,"category":"candidate_issuer_staging_refused_preserve_evidence"}')
        raise SystemExit(1)
