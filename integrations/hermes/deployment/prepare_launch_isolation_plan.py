"""Prepare root-private per-profile isolation drafts without host activation.

No accounts, credentials, profile copies or systemd units are installed. Root
reads only the retained registry, never profile trees. Existing mappings are
preserved explicitly; missing scopes are proposals requiring admission checks.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
RELEASE = Path('/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1')
SUPPORT_SHA = 'd7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef'
GATES = ('account_created', 'profile_copy_verified', 'launch_binding_qualified',
         'os_boundary_qualified', 'own_and_peer_scope_qualified', 'backup_restore_qualified',
         'native_reload_qualified', 'scheduled_renewal_qualified', 'disable_restore_qualified')


def require(value):
    if not value:
        raise ValueError('isolation_plan_refused')


def draft(rows):
    require(isinstance(rows, list) and len(rows) <= 512)
    result, seen = [], set()
    for row in rows:
        require(isinstance(row, dict))
        if 'profile_home' not in row:
            continue
        uid, user, home, profile = (row[key] for key in ('uid', 'user', 'home', 'profile_home'))
        require(type(uid) is int and uid > 0 and isinstance(user, str)
                and re.fullmatch(r'[a-z][a-z0-9_-]{0,63}', user))
        for value in (home, profile):
            require(isinstance(value, str) and value.isascii() and all(32 <= ord(char) < 127 for char in value)
                    and PurePosixPath(value).is_absolute() and str(PurePosixPath(value)) == value
                    and '..' not in PurePosixPath(value).parts)
        require(PurePosixPath(profile).is_relative_to(PurePosixPath(home) / '.hermes'))
        require(not any('lswa' in part.lower() or 'legal-social-frameworks' in part.lower()
                        for part in PurePosixPath(profile).parts))
        key = (uid, profile)
        require(key not in seen)
        seen.add(key)
        ident = hashlib.sha256((user + '\0' + profile).encode()).hexdigest()[:16]
        account = 'ecbot_' + ident
        target = '/var/lib/enhanced-cognee-profiles/' + ident
        binding = row.get('verified_binding') if row.get('token_signature_valid') is True else None
        if binding is not None:
            require(isinstance(binding, dict) and set(binding) == {'sub', 'agent_id', 'tenant', 'project_id', 'roles', 'capture_policy'})
            require(all(isinstance(binding[field], str) and re.fullmatch(r'[a-z][a-z0-9_-]{0,63}', binding[field])
                        for field in ('sub', 'agent_id', 'tenant', 'project_id')))
            require(binding['roles'] in (['api_client'], ['readonly']) and binding['capture_policy'] in {'selected', 'explicit'})
            require(len(binding['tenant']) <= 32 and len(binding['project_id']) <= 32)
        proposed = dict(tenant='hermes_private', project_id='profile_' + ident,
                        sub='subject_' + ident, agent_id='agent_' + ident,
                        roles=['api_client'], capture_policy='selected')
        # Draft text is inert JSON content, not an installed/enabled unit.
        unit = '\n'.join(('[Unit]', 'Description=Proposed isolated Hermes profile ' + ident,
            '[Service]', 'Type=simple', 'User=' + account, 'Group=' + account,
            'WorkingDirectory=' + target, 'Environment=HOME=' + target,
            'Environment=HERMES_HOME=' + target + '/.hermes',
            'ExecStart=' + str(RELEASE / 'venv/bin/python') + ' -I -B -m gateway.run',
            'NoNewPrivileges=yes', 'CapabilityBoundingSet=', 'AmbientCapabilities=',
            'UMask=0077', 'ProtectSystem=strict', 'ProtectHome=yes',
            'ReadWritePaths=' + target, 'PrivateTmp=yes', 'ProtectProc=invisible',
            'RestrictSUIDSGID=yes', 'Restart=no', ''))
        result.append(dict(profile_id=ident, source_user=user, source_uid=uid, source_profile=profile,
            proposed_user=account, proposed_uid=None, proposed_home=target, proposed_profile=target + '/.hermes',
            existing_binding=binding, proposed_binding=None if binding else proposed,
            binding_status='preserve_existing_verified_identity' if binding else 'unconfirmed_new_private_scope',
            existing_settings_and_oauth_must_be_preserved=True, copy_status='not_started',
            launch_unit_draft=unit, launch_unit_installed=False, launch_unit_execution_qualified=False,
            requires_explicit_multiplex_configuration=True,
            gates={key: False for key in GATES}, enabled=False, admission='pending'))
    require(0 < len(result) <= 256 and len({row['proposed_user'] for row in result}) == len(result))
    return result


def main():
    require(os.geteuid() == 0 and len(sys.argv) == 1)
    os.umask(0o077)
    raw = Path(__file__).with_name('recover_launch_graph_operator.py').read_bytes()
    require(hashlib.sha256(raw).hexdigest() == SUPPORT_SHA)
    support = {'__name__': 'verified_isolation_draft_files'}
    exec(compile(raw, '<verified-isolation-draft-files>', 'exec'), support)
    read, write = support['read_file'], support['private_write']
    observation = json.loads(read(BASE / 'operator-evidence/launch-process-bindings-amadrm2i/summary.json', 0))
    require(observation.get('complete') is True and observation.get('source_revision') == BASE.name
            and observation.get('operator_helper_sha256') == '14966268b02b6f93adf384c7a48aac850b82bdf51b0a5a5203fac6f3575c17ec')
    registry = json.loads(read(BASE / 'operator-evidence/token-bindings-o7gaywzr/bindings.private.json', 0))
    plans = draft(registry['rows'])
    directory = Path(tempfile.mkdtemp(prefix='profile-isolation-plan-', dir=BASE / 'operator-evidence'))
    plan_raw = json.dumps(dict(schema=1, profiles=plans,
        qualification_scope='inert_isolation_drafts_only', fleet_launch_approved=False)).encode()
    write(directory / 'plan.private.json', plan_raw)
    result = dict(complete=True, evidence=str(directory), source_revision=BASE.name,
        operator_helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        plan_sha256=hashlib.sha256(plan_raw).hexdigest(),
        planned_profile_count=len(plans), preserved_verified_bindings=sum(row['existing_binding'] is not None for row in plans),
        unconfirmed_scope_proposals=sum(row['existing_binding'] is None for row in plans),
        account_creation_count=0, installed_unit_count=0, profiles_copied=0, credentials_issued=0,
        keys_read=False, profiles_changed=False, services_changed=False, current_launchers_preserved=True,
        all_admission_gates_closed=True, fleet_launch_approved=False)
    write(directory / 'summary.json', json.dumps(result).encode())
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('{"complete":false,"category":"isolation_plan_refused_no_secret_output"}')
        raise SystemExit(1)
