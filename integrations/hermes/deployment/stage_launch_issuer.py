"""Protected issuer code plus disabled enrollment policy; never activate fleet.

Uses the retained credential-free owner inventory. Root never enters profiles,
issues credentials, changes the application key or enables systemd units.
"""
from __future__ import annotations

from collections import Counter
import grp
import hashlib
import json
import os
from pathlib import Path
import pwd
import stat
import subprocess
import sys

BASE = Path("/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529")
BINDINGS = BASE / "operator-evidence/token-bindings-o7gaywzr/bindings.private.json"
DESTINATION = BASE / "operator-issuer-candidate"
POLICY = Path("/etc/enhanced-cognee/fleet-credentials.json")
SOURCES = {
    "renew_fleet_credentials.py":"a7432a8a6c258b2f81466f51b782dd9b53c2211a5a52fcb863f3a1567ad858bf",
    "provision_pilot_access.py":"f2bf3ec50bfd8414011aa322e027f7c266a7102d558c0b7d0518549e8a8b2cc6",
    "renew_pilot_access.py":"8fb4b4dfe3941a15755bf367c982d0aadfad7fcaac94932df9b46202d8583567",
    "fleet_credential_policy.py":"6cbda2192ad6040a8043de53eac1fc2c7ad2191dd9175322e1608d285bab8102",
    "fleet_credential_lifecycle.py":"f9e16e1629710d839b45cdb21eadd81787cce66c160b5d25814fe039feef5a62"}
SHARED_SHA256 = "d7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef"


def draft(rows,executable,origin,administrative_users):
    selected = [r for r in rows if "profile_home" in r]
    counts = Counter(r["uid"] for r in selected)
    policy,plans = [],[]
    for row in selected:
        digest = hashlib.sha256((row["user"]+"\x00"+row["profile_home"]).encode()).hexdigest()[:16]
        verified = row.get("verified_binding") if row.get("token_signature_valid") is True else None
        blockers = ["reload_unqualified","launch_binding_unqualified","backup_membership_unqualified","os_boundary_unqualified"]
        if counts[row["uid"]] > 1:
            blockers.append("shared_launch_uid")
        if row["user"] in administrative_users:
            blockers.append("administrative_runtime_identity")
        plan = {"user":row["user"],"uid":row["uid"],"profile_home":row["profile_home"],
                "existing_verified_binding":verified,"admission":"pending","blockers":blockers}
        plans.append(plan)
        if verified is not None and (verified["roles"] != ["api_client"] or verified["capture_policy"] != "selected"):
            blockers.append("existing_role_or_capture_requires_manual_reissue_plan")
            continue
        scope = verified or {"tenant":"qualification","project_id":"pending_"+digest,
            "sub":"pending_subject_"+digest,"agent_id":"pending_agent_"+digest}
        policy.append({"name":"profile_"+digest,"enabled":False,"user":row["user"],"uid":row["uid"],
            "home":row["home"],"profile":row["profile_home"],"tenant":scope["tenant"],"project_id":scope["project_id"],
            "subject":scope["sub"],"agent_id":scope["agent_id"],"roles":["api_client"],"lifetime_seconds":86400,
            "origin":origin,"executable":executable,"reload_qualified":False,"launch_binding_qualified":False,
            "backup_qualified":False,"os_boundary_qualified":False})
        plan["policy_scope_source"] = "verified_existing_binding" if verified else "unconfirmed_proposal_only"
    return {"schema":1,"profiles":policy},plans


def main():
    if os.geteuid() != 0:
        raise ValueError("local_root_operator_required")
    upgrade = sys.argv[1:] == ["--upgrade-disabled"]
    if sys.argv[1:] and not upgrade:raise ValueError("fixed_staging_action_required")
    destination = BASE / "operator-issuer-candidate-v2" if upgrade else DESTINATION
    os.umask(0o077)
    raw = Path(__file__).with_name("recover_launch_graph_operator.py").read_bytes()
    if hashlib.sha256(raw).hexdigest() != SHARED_SHA256:
        raise ValueError("reviewed_file_support_required")
    shared = {"__name__":"verified_issuer_staging_files"}
    exec(compile(raw,"<verified-issuer-staging-files>","exec"),shared)
    read,write = shared["read_file"],shared["private_write"]
    accepted = json.loads(read(BASE / "operator-evidence/installed-worker-projection-after-rotation/summary.json",0))
    if accepted.get("complete") is not True or accepted.get("post_rotation_qualification") is not True:
        raise ValueError("post_rotation_acceptance_required")
    rows = json.loads(read(BINDINGS,0))["rows"]
    source = {}
    for name,expected in SOURCES.items():
        raw = Path(__file__).with_name(name).read_bytes()
        if len(raw) > 65536 or hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("reviewed_issuer_source_required")
        source[name] = raw
    policy_module = {"__name__":"verified_disabled_policy"}
    exec(compile(source["fleet_credential_policy.py"],"<verified-disabled-policy>","exec"),policy_module)
    administrators = set()
    for row in rows:
        if "profile_home" not in row:
            continue
        account = pwd.getpwnam(row["user"])
        if account.pw_uid != row["uid"] or account.pw_dir != row["home"]:
            raise ValueError("inventory_account_binding_changed")
        groups = {grp.getgrgid(gid).gr_name for gid in os.getgrouplist(account.pw_name,account.pw_gid)}
        if groups & {"root","sudo","docker","lxd","incus-admin"}:
            administrators.add(account.pw_name)
    policy,plans = draft(rows,policy_module["EXECUTABLE"],policy_module["ORIGIN"],administrators)
    policy_module["validate"](policy)
    if upgrade:
        policy = policy_module["load"](POLICY)
        if any(row["enabled"] for row in policy["profiles"]):raise ValueError("disabled_existing_policy_required")
    if (not upgrade and os.path.lexists(POLICY)) or os.path.lexists(destination):
        raise ValueError("existing_issuer_configuration_preserved")
    # Parent protection is checked without entering any profile path.
    for directory in (destination.parent,POLICY.parent):
        for item in [*reversed(directory.parents),directory]:
            info = item.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
                raise ValueError("protected_issuer_destination_required")
    evidence = BASE / "operator-evidence" / ("issuer-preparation-v2" if upgrade else "issuer-preparation")
    evidence.mkdir(mode=0o700)
    write(evidence / "admission.private.json",json.dumps({"inventory":str(BINDINGS),"profiles":plans}).encode())
    destination.mkdir(mode=0o755)
    destination.chmod(0o755)
    for name,raw in source.items():
        write(destination / name,raw)
        (destination / name).chmod(0o644)
    if not upgrade:write(POLICY,json.dumps(policy).encode())
    result = {"complete":False,"evidence":str(evidence),"issuer_candidate":str(destination),"existing_policy_preserved":upgrade,
        "inventoried_profile_homes":len(plans),"disabled_policy_entries":len(policy["profiles"]),
        "verified_existing_bindings":sum(p["existing_verified_binding"] is not None for p in plans),
        "existing_qualification_bindings":sum(p["existing_verified_binding"] is not None
            and p["existing_verified_binding"]["tenant"] == "qualification" for p in plans),
        "administrative_owner_bindings":sum(p["existing_verified_binding"] is not None
            and "administrative_runtime_identity" in p["blockers"] for p in plans),
        "signing_key_changed":False,"profiles_changed":False,"credentials_issued":0,"timer_enabled":False,
        "installed_issuer_qualified":False,"scheduled_firing_qualified":False,"fleet_launch_approved":False}
    process = subprocess.run([str(BASE / "runtime/bin/python"),"-I","-B",str(destination / "renew_fleet_credentials.py")],
        capture_output=True,timeout=30,cwd="/",env={"PATH":"/usr/bin:/bin","HOME":"/","LANG":"C.UTF-8","PYTHONDONTWRITEBYTECODE":"1"})
    if process.returncode == 0 and len(process.stdout) <= 16384:
        receipt = json.loads(process.stdout)
        if receipt.get("complete") is True and receipt.get("enabled_profiles") == 0 and receipt.get("credentials_published") == 0:
            result.update(complete=True,protected_disabled_issuer_preflight_passed=True,source_files_verified=len(source))
    if not result["complete"]:
        result["category"] = "disabled_issuer_preflight_incomplete_preserve_evidence"
    write(evidence / "summary.json",json.dumps(result).encode())
    print(json.dumps(result))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        allowed = {"local_root_operator_required","reviewed_file_support_required","post_rotation_acceptance_required",
            "reviewed_issuer_source_required","inventory_account_binding_changed","existing_issuer_configuration_preserved",
            "protected_issuer_destination_required","duplicate_policy_binding"}
        reason = str(error) if type(error) is ValueError and str(error) in allowed else "protected_input_or_policy_error"
        print(json.dumps({"complete":False,"category":"issuer_staging_refused_no_secret_output","reason":reason}))
        raise SystemExit(1)
