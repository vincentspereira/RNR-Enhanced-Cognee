"""Keep strict durable snapshots; omit reviewed telemetry runtime outputs.

Installed hermes-telemetry budget.py writes telemetry/enforcement_mode solely
for out-of-process dashboards. The running guard reads its in-memory setting,
not this file. Its FileHandler appends telemetry/telemetry.log, which remains
in place like the existing logs-directory exclusion. Configuration and budget
files remain ordinary strict payloads.
V3 and its historical refusals remain unchanged. No telemetry mode is changed.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import stat

V3_SHA = 'e32266d8a797eeaca2a32247f861cbf725341cce960eeb73d3db57987c99c106'
TELEMETRY_WRITER_SHA = '7a190c51c325e1b0da9b9ce5a7579b6748ccddd90878c649f39aad05d166578f'
TELEMETRY_REGISTER_SHA = '9aab5daed22e5cce4794443d2d522c0e0b1e289593578869112dba95d19c39a9'


def definitions():
    path = Path(__file__).with_name('capture_main_operational_profile_v3.py')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != V3_SHA:
        raise ValueError('main_v3_source_pin_refused')
    core = {'__name__': 'verified_main_capture_v3', '__file__': str(path)}
    exec(compile(raw, '<verified-main-capture-v3>', 'exec'), core)
    original_coordination = core['coordination_path']
    original_omission = core['omission_reason']

    def display_projection(relative, name):
        return relative == 'telemetry' and (name == 'enforcement_mode' or
            re.fullmatch(r'\.enforcement_mode\.[a-z0-9_]{8}\.tmp', name) is not None)

    def coordination(relative, name):
        return (display_projection(relative, name) or
                relative == 'telemetry' and name == 'telemetry.log' or
                original_coordination(relative, name))

    def omission(relative, name, info):
        if relative == 'telemetry' and name == 'telemetry.log' and stat.S_ISREG(info.st_mode):
            core['require'](info.st_uid == os.geteuid() and info.st_nlink == 1
                            and not info.st_mode & 0o7002)
            return 'diagnostic_logs_retained_in_place'
        if display_projection(relative, name) and stat.S_ISREG(info.st_mode):
            core['require'](info.st_uid == os.geteuid() and info.st_nlink == 1
                            and not info.st_mode & 0o7022 and info.st_size <= 16)
            return 'live_process_coordination_not_restored'
        return original_omission(relative, name, info)

    core['coordination_path'] = coordination
    core['omission_reason'] = omission
    return core


CORE = definitions()
CaptureError = CORE['CaptureError']
MAX_ARCHIVE = CORE['MAX_ARCHIVE']
MAX_MANIFEST = CORE['MAX_MANIFEST']
MAX_ENTRIES = CORE['MAX_ENTRIES']


capture = CORE['capture']
restore = CORE['restore']
