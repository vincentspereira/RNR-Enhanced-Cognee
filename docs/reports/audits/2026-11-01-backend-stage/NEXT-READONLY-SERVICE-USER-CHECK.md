# Next owner check - candidate imports under the API identity

Staging is complete and independently byte-verified. Do not rerun either staging
section. The current API still uses the old runtime; leave it and the renewal
timer running. This is a read-only import/permission check, not activation.

The parent verified all 7,229 candidate inventory entries against the accepted
payload and unchanged 7,235-entry original. Seven old overlay bytecode files
were omitted and one source module was added, explaining the count difference.
Python prefix/module paths and all eight module imports passed under UID 1000
with a clean environment. The equivalent check under the actual API account is
still needed; ordinary-user success does not establish service-identity access.

An initial metadata probe used -S, which intentionally skips the site processing
that sets Python 3.12's venv prefix. It was corrected to the intended -I -B
application flags; both original and candidate then resolved their own prefixes.
The failed probe and correction note are preserved; no runtime bytes changed.

## Run this one block in the ordinary Ubuntu-Hermes terminal

```bash
sudo -u enhanced-cognee-api /usr/bin/env -i \
  HOME=/nonexistent PATH=/usr/bin:/bin LANG=C.UTF-8 \
  ENHANCED_LOAD_DOTENV=0 COGNEE_LOG_FILE=false \
  COGNEE_TELEMETRY_ENABLED=0 HF_HUB_OFFLINE=1 \
  /opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101/runtime/bin/python \
  -I -B -c '
import importlib,json,os,pwd,sys
from pathlib import Path
os.chdir("/")
expected=Path("/opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101/runtime")
uid=os.geteuid()
if uid==0 or uid!=pwd.getpwnam("enhanced-cognee-api").pw_uid or sys.prefix!=str(expected):
 raise SystemExit("Identity or candidate prefix check failed; stop")
names=["src.ingestion","src.llm_summarize","src.llm_budget","src.memory_api","src.memory_daemon","src.memory_library","src.memory_queries","src.security.enterprise_auth"]
for name in names:
 try:
  module=importlib.import_module(name)
  path=expected/"lib/python3.12/site-packages"/Path(*name.split("."))
  path=path.with_suffix(".py")
  if module.__file__!=str(path) or os.access(path,os.W_OK):
   raise RuntimeError("Module path or source permission check failed")
 except Exception as exc:
  print(json.dumps({"complete":False,"failed_module":name,"error_kind":type(exc).__name__}))
  raise SystemExit(1)
print(json.dumps({"complete":True,"uid":uid,"prefix":sys.prefix,"modules_imported":len(names),"correct_module_paths":True,"source_writable":False,"api_started":False,"credentials_passed":False}))'
```

Paste the JSON output back. Expect complete=true, modules_imported=8,
correct_module_paths=true, source_writable=false and api_started=false. On any
error, stop and return it without changing permissions or starting a service.

This runs as the unprivileged API identity, not root, and deliberately supplies
no credentials. It imports application modules but never enters the application
lifespan, starts a listener or calls the database/model. It does not create the
budget ledger or change a systemd unit. The source-writable check uses read-only
permission inspection, not an attempted write and not full isolation proof.

Still open: service cutover approval/window, persistent budget provisioning,
current-day legacy usage carry-forward, ledger backup/recovery and installed
functional acceptance. A passing import check must not close those gates.
