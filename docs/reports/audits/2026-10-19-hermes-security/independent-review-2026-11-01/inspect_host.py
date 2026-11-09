"""Read-only host audit; selected settings and booleans, never credentials."""
import base64
import collections
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import yaml

ROOT = Path.cwd()
OUT = Path(__file__).parent
HOME = Path.home() / '.hermes'

def token(path):
    for line in path.read_text().splitlines():
        if line.startswith('ENHANCED_COGNEE_ACCESS_TOKEN='):
            return line.split('=', 1)[1].strip().strip('\"\'')
    return ''

def api(t, path):
    req = Request('http://127.0.0.1:28080' + path, headers={'Authorization': 'Bearer ' + t})
    try:
        with urlopen(req, timeout=20) as r:
            return r.status, json.load(r)
    except HTTPError as e:
        return e.code, {}

roles = sorted(p.name for p in (HOME / 'profiles').iterdir() if (p / 'config.yaml').is_file())
rows = []
for name in ['default'] + roles:
    home = HOME if name == 'default' else HOME / 'profiles' / name
    cfg = yaml.safe_load((home / 'config.yaml').read_text())
    env = home / '.env'
    t = token(env)
    claim = json.loads(base64.urlsafe_b64decode(t.split('.')[1] + '=' * (-len(t.split('.')[1]) % 4))) if t else {}
    ent = cfg.get('mcp_servers', {}).get('enhanced_cognee', {})
    plug = home / 'plugins/enhanced_cognee'
    plugin_files = {str(p.relative_to(plug)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in plug.rglob('*.py') if '__pycache__' not in str(p)}
    backups = [{'name': p.name, 'mode': oct(stat.S_IMODE(p.stat().st_mode)),
                'has_memory_token': bool(token(p))} for p in home.glob('.env*') if p.is_file() and p != env]
    code, status = api(t, '/v1/memories/status')
    rows.append({'role': name, 'env_mode': oct(stat.S_IMODE(env.stat().st_mode)),
                 'token_present': bool(t), 'claims_unverified': True,
                 'token_ttl_days': round((claim.get('exp', 0) - claim.get('iat', 0))/86400, 5),
                 'token_remaining_days': round((claim.get('exp', 0) - time.time())/86400, 5),
                 'token_project_matches': claim.get('project_id') == name.replace('-', '_'),
                 'authenticated_status_code': code,
                 'status_project_matches': status.get('project_id') == name.replace('-', '_'),
                 'provider': cfg.get('memory', {}).get('provider'),
                 'plugin_enabled': 'enhanced_cognee' in cfg.get('plugins', {}).get('enabled', []),
                 'memory_toolset_not_disabled': 'memory' not in cfg.get('agent', {}).get('disabled_toolsets', []),
                 'memory_in_cli_allowlist': 'memory' in cfg.get('platform_toolsets', {}).get('cli', []),
                 'mcp_groups': ent.get('args', [])[-1] if ent.get('args') else None,
                 'mcp_command_exists': Path(ent.get('command', '/nonexistent')).is_file(),
                 'mcp_args_script_matches': ent.get('args', [None, None])[1] == str(HOME / 'mcp-servers/enhanced-cognee/server.py'),
                 'mcp_env_placeholder_exact': ent.get('env') == {'ENHANCED_COGNEE_ACCESS_TOKEN': '${ENHANCED_COGNEE_ACCESS_TOKEN}'},
                 'plugin_files': plugin_files,
                 'env_backups': backups})
(OUT / 'profile-settings.json').write_text(json.dumps(rows, indent=2, sort_keys=True))
print(json.dumps({'profiles': len(roles), 'with_default': len(rows),
                  'providers': dict(collections.Counter(r['provider'] for r in rows)),
                  'groups_fleet': dict(collections.Counter(r['mcp_groups'] for r in rows if r['role'] != 'default')),
                  'all_env_0600': all(r['env_mode'] == '0o600' for r in rows),
                  'all_status_authenticated_and_project_scoped': all(r['authenticated_status_code'] == 200 and r['status_project_matches'] for r in rows),
                  'token_ttl_days': sorted(set(r['token_ttl_days'] for r in rows)),
                  'token_remaining_range_days': [min(r['token_remaining_days'] for r in rows), max(r['token_remaining_days'] for r in rows)],
                  'all_plugin_enabled': all(r['plugin_enabled'] for r in rows),
                  'all_memory_toolsets_enabled': all(r['memory_toolset_not_disabled'] and r['memory_in_cli_allowlist'] for r in rows),
                  'all_mcp_definition_selected_fields_match': all(r['mcp_command_exists'] and r['mcp_args_script_matches'] and r['mcp_env_placeholder_exact'] for r in rows),
                  'plugin_file_sets_identical': len({json.dumps(r['plugin_files'], sort_keys=True) for r in rows}) == 1,
                  'token_bearing_env_backups': sum(b['has_memory_token'] for r in rows for b in r['env_backups']),
                  'env_backups_with_unsafe_modes': sum(b['mode'] != '0o600' for r in rows for b in r['env_backups'])}, indent=2))
for name in ['media-producer', 'legal-specialist', 'devops-engineer', 'chief-of-staff', 'default']:
    r = next(r for r in rows if r['role'] == name)
    print('SPOT', json.dumps({k: r[k] for k in ['role', 'mcp_groups', 'provider', 'env_mode', 'authenticated_status_code', 'status_project_matches']}))
state_path = Path('/opt/enhanced-cognee-memory/fleet-renewal/state.json')
try:
    s = json.loads(state_path.read_text())
    # Key names only first; do not dump arbitrary state or token-like values.
    print('RENEWAL_STATE_KEYS', sorted(s))
except (OSError, ValueError) as e:
    print('RENEWAL_STATE_ERROR', type(e).__name__)
print('SERVER_SOURCE_EQUALS_INSTALLED', (ROOT / 'integrations/hermes/enhanced_cognee_mcp/server.py').read_bytes() == (HOME / 'mcp-servers/enhanced-cognee/server.py').read_bytes())
# Existing test-scope counts only: no record content or identifiers in output.
t = token(HOME / 'profiles/web-researcher/.env')
code, data = api(t, '/v1/memories?limit=200&include_shared=false')
rs = data if isinstance(data, list) else data.get('results', [])
print('FUNCTIONAL_SUITE_PREFLIGHT', json.dumps({'status': code, 'own_visible_active_rows': len(rs), 'categories': dict(collections.Counter(r.get('category') for r in rs)), 'any_non_test_category': any(r.get('category') != 'comprehensive' for r in rs)}))
# Save ordinary command output only from explicitly safe metadata commands.
commands = {
 'host': ['uname', '-sr'],
 'disk': ['df', '-h', '/', '/var/lib', '/var/backups'],
 'inodes': ['df', '-i', '/var/lib', '/var/backups'],
 'services': ['systemctl', 'is-active', 'enhanced-cognee-api', 'enhanced-cognee-postgres', 'enhanced-cognee-qdrant', 'enhanced-cognee-graph', 'enhanced-cognee-cache', 'enhanced-cognee-index'],
 'timers': ['systemctl', 'list-timers', '--all', '--no-pager', '--no-legend'],
 'renew_timer': ['systemctl', 'show', 'ec-hermes-memory-token-renew.timer', '-p', 'Id', '-p', 'ActiveState', '-p', 'NextElapseUSecRealtime', '-p', 'LastTriggerUSec', '-p', 'TimersCalendar', '-p', 'RandomizedDelayUSec', '-p', 'Persistent'],
 'backup_timer': ['systemctl', 'show', 'enhanced-cognee-qualified-fleet-backup-v2.timer', '-p', 'Id', '-p', 'ActiveState', '-p', 'NextElapseUSecMonotonic', '-p', 'TimersMonotonic', '-p', 'LastTriggerUSec', '-p', 'Persistent'],
 'job_results': ['systemctl', 'show', 'ec-hermes-memory-token-renew.service', 'enhanced-cognee-qualified-fleet-backup-v2.service', 'enhanced-cognee-backup.service', 'enhanced-cognee-profile-backup.service', '-p', 'Id', '-p', 'Result', '-p', 'ExecMainStatus', '-p', 'ExecMainExitTimestamp'],
 'journal_size': ['journalctl', '--disk-usage'],
 'receipt_permissions': ['stat', '-c', '%a %U:%G %n', '/etc/enhanced-cognee', '/etc/enhanced-cognee/llm.json', '/opt/enhanced-cognee-memory/fleet-renewal/state.json', '/var/lib/enhanced-cognee-rotation', '/var/backups/enhanced-cognee'],
 'journal_retention': ['systemd-analyze', 'cat-config', 'systemd/journald.conf']}
for label, cmd in commands.items():
    run = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    text = '$ ' + ' '.join(cmd) + '\nexit=' + str(run.returncode) + '\n' + run.stdout + run.stderr
    (OUT / (label + '.txt')).write_text(text)
print('METADATA_COMMAND_FILES', len(commands))
