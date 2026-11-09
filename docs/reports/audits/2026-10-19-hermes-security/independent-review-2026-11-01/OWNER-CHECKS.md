# Owner-only evidence still needed

These are READ-ONLY checks, not permission to repair or restart anything.
Review the commands before running them in Vincent's Ubuntu-Hermes terminal.
Paste back only the printed summaries. Do not paste credential files.

Do not run the full verifier as root from the writable deployment virtual
environment. Finding F01 identifies that trust boundary as unsafe. The commands
below use the OS interpreter and fixed inline code instead of importing project
modules or running the renewal/provisioning helpers.

## 1. Rotation receipt summaries only

```bash
sudo /usr/bin/python3 -I -c 'import json,pathlib; root=pathlib.Path("/var/lib/enhanced-cognee-rotation"); rows=[]
for candidate in sorted(root.glob("candidate-*")):
 for path in sorted(candidate.glob("execution-*.json")):
  try:
   data=json.loads(path.read_text()); family=data.get("family"); complete=data.get("complete") is True
   rows.append({"file":str(path),"family":family if family in {"postgresql","valkey","qdrant","application","arcadedb","arcadedb-apply"} else "other","complete":complete})
  except (OSError,ValueError):
   rows.append({"file":str(path),"readable_json":False})
print(json.dumps(rows,indent=2))'
```

This reads receipt metadata only. It does not rotate credentials or prove that
old credentials are currently rejected. A previous successful receipt is dated
execution evidence, not a fresh credential test.

## 2. LLM configuration protection, without values

```bash
sudo /usr/bin/python3 -I -c 'import json,pathlib,stat; p=pathlib.Path("/etc/enhanced-cognee/llm.json"); s=p.stat(); d=json.loads(p.read_text()); print(json.dumps({"path":str(p),"uid":s.st_uid,"gid":s.st_gid,"mode":oct(stat.S_IMODE(s.st_mode)),"api_key_present":bool(d.get("api_key")),"model_is_expected":d.get("model")=="GLM-5.3-Flash","cap_is_50000":d.get("daily_token_cap")==50000}))'
```

This verifies presence and file protection, not the key's uniqueness. Runtime
credential copies and the daemon's environment are expected. Do not dump them.
A separate owner-reviewed equality-only scan is needed to check accidental
copies without printing the key; do not recursively dump /etc or profiles.

## 3. Current recovery coverage

Provide existing, sanitised receipt summaries for:

- The most recent canonical database backup and successful disposable restore.
- The most recent backup and restore of the CURRENT gateway home plus all 44
  ~/.hermes/profiles roles, including the four specialists and current tokens.
- The qualified inactive 41-candidate backup's last successful run and membership.
- Any separate current gateway backup job that was not visible in this review.
- An owner-tested failure-alert route and the date of the last recovery drill.

No new restore drill, live credential test, renewal run or service restart was
performed by this audit. Those require separately scoped owner approval.

## 4. Decisions recommended after reading the report

1. Authorise a separate remediation task for F01-F04 first. Do not activate new
   workloads or deploy the source-only renewal change before reviewing it.
2. Repair the verifiers so failed checks return a nonzero exit and skipped
   privilege-only checks are explicit. Preserve this audit's failed outputs.
3. Reconcile current-profile backup membership and client token-refresh evidence.
4. Re-run only targeted acceptance checks after approved fixes; do not repeat
   completed native/memory qualification as a substitute for these findings.
