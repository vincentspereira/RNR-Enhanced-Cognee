"""Explicit operator recovery for one disabled candidate's expired credential.

Unattended renewal continues to use the unchanged fail-closed lifecycle. This
transaction admits only an expired token with the fixed policy identity and a
real HTTP 401, plus fresh valid ordinary credentials supplied by root. No root
signing key enters the profile owner. Preserve journals and previous settings.
"""
from __future__ import annotations
import json
import os
import time
import uuid


def recover(core, renewal, lifecycle, directory, bundle, uid, entry, *, checkpoint=lambda phase: None):
    if (entry.get('enabled') is not False or entry.get('reload_qualified') is not False
            or entry.get('launch_binding_qualified') is not False or entry.get('uid') != uid
            or uid != os.geteuid() or uid == 0):
        raise ValueError('disabled_candidate_operator_recovery_required')
    if not isinstance(bundle, dict) or set(bundle) != {'token', 'expired', 'altered', 'claims'}:
        raise ValueError('ordinary_recovery_bundle_required')
    identity = dict(sub=entry['subject'], agent_id=entry['agent_id'], tenant=entry['tenant'],
                    project_id=entry['project_id'], roles=['api_client'], capture_policy='selected')
    if core['IDENTITY'] != identity:
        raise ValueError('fixed_recovery_identity_required')
    claims = renewal['token_claims'](core, bundle['token'])
    now = int(time.time())
    if claims != bundle['claims'] or not 0 <= now - claims['iat'] <= 120 or claims['exp'] - claims['iat'] != 86400:
        raise ValueError('fresh_fixed_lifetime_recovery_required')
    original = core['read_private_at'](directory, '.env', uid)[0]
    previous = renewal['environment'](core, original)
    old = renewal['token_claims'](core, previous)
    if old['exp'] > now or previous == bundle['token'] or core['api_status'](previous)[0] != 401:
        raise ValueError('expired_candidate_refusal_required')
    # token_claims enforces the exact identity/roles and bounded lifetime even
    # for an expired value; root policy authorizes this recovery independently.
    reconciled = renewal['reconcile'](core, directory, uid, original)
    saved = {name: core['read_private_at'](directory, name, uid)[0]
             for name in ('config.yaml', 'enhanced_cognee.json', 'auth.json')}
    settings = json.loads(saved['enhanced_cognee.json'])
    if (settings.get('base_url') != 'http://127.0.0.1:28080' or settings.get('capture_policy') != 'selected'
            or type(settings.get('include_shared')) is not bool):
        raise ValueError('fixed_candidate_settings_required')
    for token in (None, bundle['expired'], bundle['altered']):
        if core['api_status'](token)[0] != 401:
            raise ValueError('recovery_refusal_control_failed')
    lifecycle['accepted_status'](core, bundle['token'])
    updated = renewal['environment'](core, original, bundle['token'])
    ident = uuid.uuid4().hex
    backup, candidate = '.env-before-cognee-renew-' + ident, '.env-cognee-renew-' + ident
    name = '.cognee-renewal-' + ident + '.json'
    journal = dict(backup=backup, candidate=candidate, before=renewal['digest'](original), after=renewal['digest'](updated))
    for path, raw in ((backup, original), (candidate, updated), (name, json.dumps(journal).encode())):
        core['create_private_at'](directory, path, raw)
        if core['read_private_at'](directory, path, uid)[0] != raw:
            raise ValueError('recovery_staging_readback_failed')
    os.fsync(directory)
    checkpoint('prepared')
    if (core['read_private_at'](directory, '.env', uid)[0] != original
            or any(core['read_private_at'](directory, name, uid)[0] != raw for name, raw in saved.items())):
        raise ValueError('candidate_changed_before_recovery')
    os.replace(candidate, '.env', src_dir_fd=directory, dst_dir_fd=directory)
    os.fsync(directory)
    checkpoint('published')
    if (core['read_private_at'](directory, '.env', uid)[0] != updated
            or any(core['read_private_at'](directory, name, uid)[0] != raw for name, raw in saved.items())):
        raise ValueError('candidate_recovery_preservation_failed')
    lifecycle['accepted_status'](core, bundle['token'])
    renewal['finish'](core, directory, name, journal, 'published')
    return dict(complete=True, expired_candidate_recovered=True, preserved_settings_and_oauth=True,
                preserved_previous_environment=True, interrupted_attempts_reconciled=reconciled,
                unattended_renewal_qualified=False, timer_activation_approved=False)
