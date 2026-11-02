# Read-only diagnostic for the refused plan

The helper is already correctly installed. Do NOT repeat its installation, alter
permissions, run --prepare, install an override or restart a service.

This single command runs trusted OS Python, checks the exact protected helper,
then calls only its read-only preflight functions. It identifies the first
failing stage. For the protected runtime unit it prints recognised directive
NAMES, counts and comparison booleans only, never its values or raw contents.
No credential JSON or key file is read. No application code is imported.

Run from your ordinary Ubuntu-Hermes terminal. Sudo asks locally if needed; do not
paste a password. Return the JSON. If it reports a refusal, stop; do not weaken a
check. If every check now passes, it also returns the actual validated plan and
digest so that no extra blind --plan retry is needed. It never runs --prepare.

```bash
sudo /usr/bin/python3 -I -S -B -c '
import ast,hashlib,json,os,runpy,shlex,stat,sys
from pathlib import Path

def unit_structure(raw,h):
 try:
  text=raw.decode("ascii")
 except UnicodeError:
  return {"ascii":False,"raw_values_printed":False}
 known=set().union(*h["SECTIONS"].values())|{"EnvironmentFile","ReadOnlyPaths","ReadWritePaths","BindPaths","BindReadOnlyPaths","PassEnvironment","UnsetEnvironment","ImportCredential","SetCredential","SetCredentialEncrypted","LoadCredentialEncrypted"}
 env_names={x.split("=",1)[0] for x in h["SAFE_ENV"]}|{"ENHANCED_MODEL_CACHE","ENHANCED_INDEX_CONFIG","HOME","PYTHONPATH","PYTHONHOME","HF_HOME","XDG_CACHE_HOME","LANG","LC_ALL","TZ"}
 rows=[]
 counts={}
 for number,line in enumerate(text.splitlines(),1):
  value=line.strip()
  if not value or value.startswith(("#",";")): continue
  row={"line":number,"leading_whitespace":line!=line.lstrip()}
  if value.startswith("[") and value.endswith("]"):
   section=value[1:-1]
   row["section"]=section if section in h["SECTIONS"] else "OTHER"
  elif "=" in value:
   key,body=value.split("=",1)
   label=key if key in known else "OTHER"
   row.update({"directive":label,"empty":body==""})
   counts[label]=counts.get(label,0)+1
   if key in {"User","Group"}: row["matches_api_identity"]=body=="enhanced-cognee-api"
   if key=="WorkingDirectory": row["matches_old_candidate"]=body==h["OLD"]
   if key=="ExecStart": row["matches_old_launcher"]=body==h["OLD"]+"/runtime/bin/python -m src.memory_daemon api"
   if key=="Environment":
    try:
     pairs=shlex.split(body)
     names=[part.split("=",1)[0] if "=" in part else "" for part in pairs]
     row["known_variable_names"]=[name for name in names if name in env_names]
     row["other_variable_count"]=sum(name not in env_names for name in names)
     row["matches_approved_literal_allowlist"]=bool(pairs) and set(pairs)<=h["SAFE_ENV"]
    except ValueError:
     row["environment_syntax_valid"]=False
  else: row["malformed_line"]=True
  rows.append(row)
 return {"ascii":True,"directive_counts":counts,"missing_required_launch_directives":[key for key in ("User","Group","WorkingDirectory","ExecStart") if not counts.get(key)],"rows":rows,"raw_values_printed":False}

stage="protected_helper_identity"
result={"read_only":True,"checks":[],"services_restarted":False,"ledger_created":False}
h=None
snapshot=None
try:
 if os.geteuid()!=0 or os.getegid()!=0: raise RuntimeError("root_required")
 p=Path("/opt/enhanced-cognee-memory/security-first-helper/prepare_security_first_cutover.py")
 for item in reversed(p.parents):
  s=item.lstat()
  if not stat.S_ISDIR(s.st_mode) or s.st_uid!=0 or s.st_gid!=0 or s.st_mode & 0o7022: raise RuntimeError("helper_ancestor_refused")
 s=p.lstat()
 if not stat.S_ISREG(s.st_mode) or s.st_uid!=0 or s.st_gid!=0 or s.st_nlink!=1 or stat.S_IMODE(s.st_mode)!=0o644: raise RuntimeError("helper_file_refused")
 data=p.read_bytes()
 expected="d9424c108646f4a88a9cb8babad92d7335497b194d9fc80e6b27452e91731f63"
 if hashlib.sha256(data).hexdigest()!=expected: raise RuntimeError("helper_hash_refused")
 codes={n.args[0].value for n in ast.walk(ast.parse(data)) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=="Refusal" and n.args and isinstance(n.args[0],ast.Constant) and isinstance(n.args[0].value,str)}
 h=runpy.run_path(str(p),run_name="__readonly_diagnostic__")
 for stage,function in (("runtime_guard",h["runtime_guard"]),("output_guard",h["check_output"]),("unit_inventory",h["inventory_sources"]),("loaded_unit_state",h["read_loaded"])):
  value=function()
  if stage=="loaded_unit_state" and value!=h["EXPECTED_LOADED"]: raise h["Refusal"]("inventory_or_loaded_or_candidate_drift")
  result["checks"].append({"stage":stage,"passed":True})
 stage="protected_runtime_unit_read"
 raw=h["read_protected"](h["SOURCES"][2])
 result["runtime_unit_structure"]=unit_structure(raw,h)
 stage="protected_runtime_unit_parse"
 h["parse_unit"](raw,launch=True)
 result["checks"].append({"stage":stage,"passed":True})
 stage="snapshot_collection"
 snapshot=h["collect_snapshot"]()
 result["checks"].append({"stage":stage,"passed":True})
 stage="plan_validation"
 plan=h["plan_from_snapshot"](snapshot)
 result.update({"complete":True,"plan":plan,"plan_sha256":h["digest"](h["canonical"](plan))})
except Exception as exc:
 result.update({"complete":False,"failed_stage":stage,"error_kind":type(exc).__name__})
 if h is not None and isinstance(exc,h["Refusal"]) and len(exc.args)==1 and exc.args[0] in codes: result["fixed_reason_code"]=exc.args[0]
 if isinstance(exc,OSError): result["errno"]=exc.errno
print(json.dumps(result,sort_keys=True))
sys.exit(0 if result.get("complete") else 1)
'
```

This checks metadata and code bytes, not a service restart or full API boot. The
existing API and its current optional model route remain untouched. A diagnostic
failure does not authorise changing the protected runtime unit or the helper.
